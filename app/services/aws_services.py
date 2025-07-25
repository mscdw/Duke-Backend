import boto3
import json
import uuid
import httpx
from io import BytesIO
from PIL import Image
from botocore.exceptions import ClientError
from app.models.aws_models import FaceInfo, BoundingBox  # Assuming these are your Pydantic models
from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger("aws-services")

DEFAULT_COLLECTION_ID = 'new-face-collection-11'
rekognition = boto3.client("rekognition", region_name="us-east-2")

# --- NEW: Configuration for Central API ---
try:
    settings = get_settings()
    central_base_url = settings.CENTRAL_BASE
    users_url = f"{central_base_url.rstrip('/')}/users/"
    # Use the same SSL verification setting as other schedulers for consistency
    verify_ssl = getattr(settings, "AVIGILON_API_VERIFY_SSL", True)
except Exception as e:
    logger.error(f"Failed to get settings for Central API: {e}. User creation will fail.", exc_info=True)
    central_base_url = None
    users_url = None
    verify_ssl = True


# --- HELPER FUNCTIONS (MODIFIED TO RETURN ERROR MESSAGES) ---

def search_faces_by_image(image_bytes: bytes, collection_id: str = DEFAULT_COLLECTION_ID, face_match_threshold: float = 90.0):
    """
    Search for faces in the collection using an image. This is a more direct approach
    than searching for users, and allows for more granular error handling.
    Returns:
        (response_dict, None) on success.
        (None, error_message_string) on a handled ClientError.
    """
    try:
        params_to_log = {
            'CollectionId': collection_id, 'Image': f"<bytes of size {len(image_bytes)}>",
            'FaceMatchThreshold': face_match_threshold, 'MaxFaces': 1
        }
        logger.info(f"Calling SearchFacesByImage with params: {json.dumps(params_to_log, indent=2)}")

        response = rekognition.search_faces_by_image(
            CollectionId=collection_id,
            Image={'Bytes': image_bytes},
            FaceMatchThreshold=face_match_threshold,
            MaxFaces=1
        )
        return response, None  # Success: return response and no error
    except ClientError as e:
        if 'InvalidParameterException' in e.response['Error']['Code']:
            error_msg = e.response['Error']['Message']
            logger.warning(f"SearchFacesByImage failed with handled error: {error_msg}")
            return None, error_msg
        logger.error(f"Error searching faces: {e.response['Error']}", exc_info=True)
        raise # Re-raise unhandled exceptions


def index_faces(image_bytes: bytes, collection_id: str = DEFAULT_COLLECTION_ID, max_faces: int = 1, quality_filter: str = 'NONE'):
    """
    Index a single face.
    Returns:
        (response_dict, None) on success.
        (None, error_message_string) on a handled ClientError.
    """
    try:
        params_to_log = {
            'CollectionId': collection_id, 'Image': f"<bytes of size {len(image_bytes)}>",
            'MaxFaces': max_faces, 'QualityFilter': quality_filter
        }
        logger.info(f"Calling IndexFaces with params: {json.dumps(params_to_log, indent=2)}")
        
        response = rekognition.index_faces(
            CollectionId=collection_id,
            Image={'Bytes': image_bytes},
            MaxFaces=max_faces,
            QualityFilter=quality_filter,
            DetectionAttributes=['DEFAULT']
        )
        return response, None # Success: return response and no error
    except ClientError as e:
        if 'InvalidParameterException' in e.response['Error']['Code']:
            # Handled failure: return no response but include the AWS error message
            error_msg = e.response['Error']['Message']
            logger.warning(f"IndexFaces failed with handled error: {error_msg}")
            return None, error_msg
        logger.error(f"Error indexing faces: {e.response['Error']}", exc_info=True)
        raise # Re-raise unhandled exceptions


# --- NEW HELPER FUNCTIONS FOR USER CREATION ---

def create_rekognition_user(user_id: str, collection_id: str = DEFAULT_COLLECTION_ID):
    """Creates a new user in the Rekognition collection."""
    try:
        logger.info(f"Creating user '{user_id}' in Rekognition collection '{collection_id}'.")
        rekognition.create_user(CollectionId=collection_id, UserId=user_id)
        logger.info(f"Successfully created user '{user_id}' in Rekognition.")
        return True, None
    except ClientError as e:
        error_msg = e.response['Error']['Message']
        logger.error(f"Failed to create user '{user_id}' in Rekognition: {error_msg}", exc_info=True)
        return False, error_msg


def associate_face_to_user(user_id: str, face_id: str, collection_id: str = DEFAULT_COLLECTION_ID):
    """Associates a face with a user in the Rekognition collection."""
    try:
        logger.info(f"Associating face '{face_id}' with user '{user_id}'.")
        rekognition.associate_faces(
            CollectionId=collection_id,
            UserId=user_id,
            FaceIds=[face_id]
        )
        logger.info(f"Successfully associated face '{face_id}' with user '{user_id}'.")
        return True, None
    except ClientError as e:
        error_msg = e.response['Error']['Message']
        logger.error(f"Failed to associate face '{face_id}' with user '{user_id}': {error_msg}", exc_info=True)
        return False, error_msg


def get_user_by_face_id_sync(face_id: str):
    """
    Synchronously gets a user from Duke-Central by their Face ID.
    This function is synchronous to be called from the sync `process_all_faces_in_image` function.
    Returns:
        (user_document_dict, None) on success.
        (None, error_message_string) on failure.
        (None, None) if user is not found (404), which is not an error.
    """
    if not users_url:
        return None, "User lookup in Central skipped: URL not configured."

    url = f"{users_url}by-face-id/{face_id}"
    try:
        logger.info(f"Querying Duke-Central for user with FaceId: {face_id}")
        with httpx.Client(verify=verify_ssl, timeout=10) as client:
            response = client.get(url)
            if response.status_code == 404:
                logger.info(f"No user found in Central for FaceId '{face_id}'. This is expected for a new person.")
                return None, None  # Not found is a valid outcome, not an error.
            
            response.raise_for_status()
            logger.info(f"Found user for FaceId '{face_id}'.")
            return response.json(), None
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error getting user from Central: {e.response.status_code} - {e.response.text}"
        logger.error(error_msg)
        return None, error_msg
    except Exception as e:
        error_msg = f"Failed to get user by FaceId '{face_id}' from Duke-Central: {e}"
        logger.error(error_msg, exc_info=True)
        return None, error_msg


def create_central_user_sync(user_id: str, face_id: str):
    """
    Synchronously creates the user record in the Duke-Central database via API call.
    This function is synchronous to be called from the sync `process_all_faces_in_image` function.
    """
    if not users_url:
        return False, "User creation in Central skipped: URL not configured."

    # The API expects '_id' as the key for the user's ID.
    payload = {"_id": user_id, "faceIds": [face_id]}
    try:
        logger.info(f"Posting new user to Duke-Central: {payload}")
        # Use a synchronous client for this call.
        with httpx.Client(base_url=central_base_url, verify=verify_ssl, timeout=30) as client:
            response = client.post("/users/", json=payload)
            response.raise_for_status()
        logger.info(f"Successfully created user '{user_id}' in Duke-Central.")
        return True, None
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error creating user in Central: {e.response.status_code} - {e.response.text}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Failed to create user '{user_id}' in Duke-Central: {e}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg


# --- PRIMARY ORCHESTRATOR FUNCTION (FINAL VERSION) ---

def process_all_faces_in_image(image_bytes: bytes, collection_id: str = DEFAULT_COLLECTION_ID) -> list:
    """
    Detects ALL faces in an image, processes each one individually,
    and returns a list of detailed results with specific failure reasons.
    This version uses a more robust Search-then-Lookup pattern.
    """
    # 1. Detect all faces and their rich attributes first
    try:
        detect_response = rekognition.detect_faces(Image={'Bytes': image_bytes}, Attributes=['ALL'])
        detected_face_details = detect_response.get('FaceDetails', [])
    except ClientError as e:
        logger.error(f"Fatal error calling DetectFaces: {e.response['Error']}", exc_info=True)
        return [{"status": "error", "error_message": f"DetectFaces API call failed: {str(e)}"}]

    if not detected_face_details:
        logger.info("No faces found by DetectFaces in the image.")
        return []

    logger.info(f"DetectFaces found {len(detected_face_details)} face(s). Processing each one.")
    
    try:
        img = Image.open(BytesIO(image_bytes))
        img_width, img_height = img.size
    except Exception as e:
        logger.error(f"Pillow could not open image bytes: ", exc_info=True)
        return [{"status": "error", "error_message": f"Image data is corrupt: {str(e)}"}]
            
    final_results = []
    
    # 2. Loop through each detected face
    for face_detail in detected_face_details:
        # Filter on Detection Confidence
        detection_confidence = face_detail.get('Confidence', 0)
        if detection_confidence < 90.0:
            logger.warning(
                f"Skipping face due to low detection confidence ({detection_confidence:.2f}%). "
                f"BoundingBox: {face_detail.get('BoundingBox')}"
            )
            final_results.append({
                "status": "skipped_low_confidence",
                "message": f"Face detected with confidence {detection_confidence:.2f}%, which is below the 90% threshold.",
                "rekognition_details": face_detail
            })
            continue  # Skip to the next face

        bbox = face_detail['BoundingBox']
        
        # 3. Crop the original image to this specific face
        left = int(bbox['Left'] * img_width)
        top = int(bbox['Top'] * img_height)
        right = int(left + (bbox['Width'] * img_width))
        bottom = int(top + (bbox['Height'] * img_height))
        
        cropped_img = img.crop((left, top, right, bottom))
        
        with BytesIO() as output:
            cropped_img.save(output, format=img.format or 'JPEG')
            cropped_image_bytes = output.getvalue()

        # 4. Process this individual cropped face
        result = {}
        try:
            # A. Search for a FACE matching the cropped image.
            search_response, search_error = search_faces_by_image(
                cropped_image_bytes,
                collection_id,
                face_match_threshold=90.0
            )

            if search_response and search_response.get("FaceMatches"):
                # A face was matched in the collection.
                first_match = search_response['FaceMatches'][0]
                matched_face_data = first_match['Face']
                matched_face_id = matched_face_data['FaceId']
                similarity = first_match['Similarity']
                
                logger.info(f"Face matched in collection with FaceId: '{matched_face_id}', Similarity: {similarity:.2f}%. Looking up user.")

                # Now, find the user associated with this FaceId.
                user_doc, user_error = get_user_by_face_id_sync(matched_face_id)

                if user_doc:
                    user_id = user_doc.get('_id')
                    logger.info(f"Found user '{user_id}' for FaceId '{matched_face_id}'.")
                    face_info = FaceInfo(
                        FaceId=matched_face_id,
                        BoundingBox=BoundingBox(**face_detail.get("BoundingBox", {})),
                        ImageId=matched_face_data.get("ImageId"),
                        Confidence=similarity
                    )
                    result = { "status": "matched", "userId": user_id, "faceId": matched_face_id, "face_info": face_info.model_dump(), "rekognition_details": face_detail }
                elif user_error:
                    # An error occurred trying to look up the user.
                    logger.error(f"Error looking up user for matched FaceId '{matched_face_id}': {user_error}")
                    result = { "status": "error", "error_message": f"Found matching face {matched_face_id} but failed to look up user.", "failure_reason": user_error, "rekognition_details": face_detail }
                else:
                    # This is a data inconsistency. The face exists in Rekognition but not in our DB.
                    logger.error(f"Data Inconsistency: FaceId '{matched_face_id}' exists in Rekognition but has no associated user in Central DB.")
                    result = { "status": "error", "error_message": f"Data inconsistency: FaceId {matched_face_id} has no user.", "rekognition_details": face_detail }
            else:
                # B. If not found, index it and capture both response and potential error
                index_response, index_error = index_faces(
                    cropped_image_bytes, collection_id, quality_filter='NONE'
                )

                if index_response and index_response.get("FaceRecords"):
                    indexed_face_record = index_response['FaceRecords'][0]
                    indexed_face_data = indexed_face_record['Face']
                    new_face_id = indexed_face_data.get("FaceId")

                    # --- NEW LOGIC FOR USER CREATION ---
                    if new_face_id:
                        user_id = f"user_{uuid.uuid4()}"
                        logger.info(f"[NEW FACE WORKFLOW - STEP 0] Indexed new face. FaceId: '{new_face_id}'. Generated new UserId: '{user_id}'.")

                        # 1. Create user in Rekognition
                        logger.info(f"[NEW FACE WORKFLOW - STEP 1] Attempting to create user in Rekognition.")
                        created_ok, rek_create_err = create_rekognition_user(user_id, collection_id)
                        if not created_ok:
                            logger.error(f"[NEW FACE WORKFLOW - STEP 1 FAILED] Rekognition user creation failed. Reason: {rek_create_err}")
                        else:
                            logger.info(f"[NEW FACE WORKFLOW - STEP 1 SUCCESS] Rekognition user created successfully.")

                        # 2. Associate face to user in Rekognition
                        associated_ok, rek_assoc_err = False, "Skipped due to user creation failure"
                        if created_ok:
                            logger.info(f"[NEW FACE WORKFLOW - STEP 2] Attempting to associate FaceId '{new_face_id}' with UserId '{user_id}'.")
                            associated_ok, rek_assoc_err = associate_face_to_user(user_id, new_face_id, collection_id)
                            if not associated_ok:
                                logger.error(f"[NEW FACE WORKFLOW - STEP 2 FAILED] Face association failed. Reason: {rek_assoc_err}")
                            else:
                                logger.info(f"[NEW FACE WORKFLOW - STEP 2 SUCCESS] Face associated successfully.")

                        # 3. Create user in Central DB via API
                        central_user_ok, central_err = False, "Skipped due to Rekognition failure"
                        if associated_ok:
                            logger.info(f"[NEW FACE WORKFLOW - STEP 3] Attempting to create user in Central DB.")
                            central_user_ok, central_err = create_central_user_sync(user_id, new_face_id)
                            if not central_user_ok:
                                logger.error(f"[NEW FACE WORKFLOW - STEP 3 FAILED] Central DB user creation failed. Reason: {central_err}")
                            else:
                                logger.info(f"[NEW FACE WORKFLOW - STEP 3 SUCCESS] Central DB user created successfully.")

                        if not (created_ok and associated_ok and central_user_ok):
                            # If any step failed, log a critical error and mark this face as failed.
                            error_detail = (
                                f"Rekognition CreateUser error: {rek_create_err}. "
                                f"Rekognition AssociateFaces error: {rek_assoc_err}. "
                                f"Central API CreateUser error: {central_err}."
                            )
                            logger.critical(
                                f"Failed to complete new user creation for FaceId '{new_face_id}'. Details: {error_detail}"
                            )
                            result = {
                                "status": "error",
                                "error_message": f"Failed to create and associate new user for FaceId {new_face_id}.",
                                "failure_reason": error_detail,
                                "rekognition_details": face_detail
                            }
                        else:
                            # All steps succeeded.
                            face_info = FaceInfo(
                                FaceId=new_face_id,
                                # The BoundingBox should be from the original DetectFaces call for consistency.
                                BoundingBox=BoundingBox(**face_detail.get("BoundingBox", {})),
                                ImageId=indexed_face_data.get("ImageId"),
                                Confidence=indexed_face_data.get("Confidence")
                            )
                            result = {
                                "status": "indexed",
                                "userId": user_id,
                                "faceId": new_face_id,
                                "face_info": face_info.model_dump(),
                                "rekognition_details": face_detail
                            }
                    else:
                        logger.error("IndexFaces response did not contain a FaceId. Cannot create user.")
                        result = {"status": "error", "error_message": "Indexing succeeded but no FaceId was returned.", "rekognition_details": face_detail}
                    # --- END OF NEW LOGIC ---
                else:
                    # C. BOTH search and index failed. Capture the specific error.
                    # The index_error is the most likely reason for failure in this path.
                    failure_reason = index_error or search_error or "Unknown failure during search/index."
                    
                    logger.warning(
                        f"Skipping face due to low quality. Rekognition reason: '{failure_reason}'. "
                        f"BoundingBox: {face_detail.get('BoundingBox')}"
                    )
                    result = {
                        "status": "skipped_low_quality",
                        "message": "Face was detected, but could not be processed, likely due to low quality (e.g., blur, occlusion, or small size).",
                        "failure_reason": failure_reason, # The exact reason from AWS
                        "rekognition_details": face_detail
                    }
            
            final_results.append(result)

        except Exception as e:
            logger.error(f"Error processing a single cropped face: ", exc_info=True)
            final_results.append({
                "status": "error", 
                "error_message": str(e), 
                "rekognition_details": face_detail
            })
            
    return final_results