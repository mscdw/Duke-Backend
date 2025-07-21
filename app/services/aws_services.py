import boto3
import json
from io import BytesIO
from PIL import Image  # <-- NEW IMPORT
from botocore.exceptions import ClientError
from app.models.aws_models import FaceInfo, BoundingBox
from app.core.logging import get_logger

logger = get_logger("aws-services")

DEFAULT_COLLECTION_ID = 'new-face-collection-2'
rekognition = boto3.client("rekognition", region_name="us-east-2")


# --- HELPER FUNCTIONS (UNCHANGED, BUT STILL NEEDED) ---

def search_faces_by_image(image_bytes: bytes, collection_id: str = DEFAULT_COLLECTION_ID, face_match_threshold: float = 90.0, max_faces: int = 1):
    """Search for a single face using a (likely cropped) image."""
    try:
        # Log-safe params
        params_to_log = {
            'CollectionId': collection_id, 'Image': f"<bytes of size {len(image_bytes)}>",
            'FaceMatchThreshold': face_match_threshold, 'MaxFaces': max_faces
        }
        logger.info(f"Calling SearchFacesByImage with params: {json.dumps(params_to_log, indent=2)}")

        response = rekognition.search_faces_by_image(
            CollectionId=collection_id,
            Image={'Bytes': image_bytes},
            FaceMatchThreshold=face_match_threshold,
            MaxFaces=max_faces
        )
        return response
    except ClientError as e:
        if 'InvalidParameterException' in e.response['Error']['Code']:
            # This is expected if the cropped image has no face or is too small
            return None
        logger.error(f"Error searching faces: {e.response['Error']}", exc_info=True)
        raise

def index_faces(image_bytes: bytes, collection_id: str = DEFAULT_COLLECTION_ID, max_faces: int = 1, quality_filter: str = 'NONE'):
    """Index a single face using a (likely cropped) image."""
    try:
        # Log-safe params
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
        return response
    except ClientError as e:
        if 'InvalidParameterException' in e.response['Error']['Code']:
            # Expected if cropped image is empty/bad
            return None
        logger.error(f"Error indexing faces: {e.response['Error']}", exc_info=True)
        raise


# --- NEW PRIMARY ORCHESTRATOR FUNCTION ---
# This function replaces 'process_face_search_and_index'

def process_all_faces_in_image(image_bytes: bytes, collection_id: str = DEFAULT_COLLECTION_ID) -> list:
    """
    Detects ALL faces in an image, processes each one individually,
    and returns a list of detailed results.
    """
    # 1. Detect all faces and their rich attributes first
    try:
        detect_response = rekognition.detect_faces(Image={'Bytes': image_bytes}, Attributes=['ALL'])
        detected_face_details = detect_response.get('FaceDetails', [])
    except ClientError as e:
        logger.error(f"Fatal error calling DetectFaces: {e}", exc_info=True)
        return [{"status": "error", "error_message": f"DetectFaces API call failed: {str(e)}"}]

    if not detected_face_details:
        logger.info("No faces found by DetectFaces in the image.")
        return [] # Return empty list, signifying no faces to process

    logger.info(f"DetectFaces found {len(detected_face_details)} face(s). Processing each one.")
    
    try:
        img = Image.open(BytesIO(image_bytes))
        img_width, img_height = img.size
    except Exception as e:
        logger.error(f"Pillow could not open image bytes: {e}", exc_info=True)
        return [{"status": "error", "error_message": f"Image data is corrupt: {str(e)}"}]
        
    final_results = []
    
    # 2. Loop through each detected face
    for face_detail in detected_face_details:
        bbox = face_detail['BoundingBox']
        
        # 3. CRITICAL: Crop the original image to this specific face
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
            # A. Search for the face
            search_response = search_faces_by_image(
                cropped_image_bytes, 
                collection_id, 
                face_match_threshold=90.0
            )  
                      
            if search_response and search_response.get("FaceMatches"):
                matched_face_data = search_response['FaceMatches'][0]['Face']
                # Create a FaceInfo object to structure the data nicely
                face_info = FaceInfo(
                    FaceId=matched_face_data.get("FaceId"),
                    BoundingBox=BoundingBox(**search_response.get("SearchedFaceBoundingBox", {})),
                    ImageId=matched_face_data.get("ImageId"),
                    Confidence=matched_face_data.get("Confidence")
                )
                result = {
                    "status": "matched",
                    "face_info": face_info.model_dump(),
                    "rekognition_details": face_detail
                }
            else:
                # B. If not found, index it
                index_response = index_faces(cropped_image_bytes, collection_id, quality_filter='NONE')
                if index_response and index_response.get("FaceRecords"):
                    indexed_face_data = index_response['FaceRecords'][0]['Face']
                    face_info = FaceInfo(
                        FaceId=indexed_face_data.get("FaceId"),
                        BoundingBox=BoundingBox(**indexed_face_data.get("BoundingBox", {})),
                        ImageId=indexed_face_data.get("ImageId"),
                        Confidence=indexed_face_data.get("Confidence")
                    )
                    result = {
                        "status": "indexed",
                        "face_info": face_info.model_dump(),
                        "rekognition_details": face_detail
                    }
                else:
                    # C. If detection worked but search/index failed, it's low quality
                    result = {
                        "status": "low_quality_face",
                        "rekognition_details": face_detail
                    }
            
            final_results.append(result)

        except Exception as e:
            logger.error(f"Error processing a single cropped face: {e}", exc_info=True)
            final_results.append({
                "status": "error", "error_message": str(e), "rekognition_details": face_detail
            })
            
    return final_results