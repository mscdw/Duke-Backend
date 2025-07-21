import boto3
import json
from botocore.exceptions import ClientError
from app.models.aws_models import FaceInfo, BoundingBox
from app.core.logging import get_logger

logger = get_logger("aws-services")

DEFAULT_COLLECTION_ID = 'new-face-collection-2'
rekognition = boto3.client("rekognition", region_name="us-east-2")


def create_collection(collection_id: str = DEFAULT_COLLECTION_ID):
    """Create a new Rekognition collection."""
    try:
        logger.info(f"Calling CreateCollection with CollectionId: '{collection_id}'")
        response = rekognition.create_collection(CollectionId=collection_id)
        # Log the full, pretty-printed JSON response
        logger.info(f"CreateCollection raw response: {json.dumps(response, indent=2)}")
        return response
    except ClientError as e:
        # Log the specific error from AWS for better debugging
        error_details = e.response.get("Error", {})
        logger.error(f"Error creating collection '{collection_id}': {error_details}", exc_info=True)
        raise


def list_collections():
    """List all Rekognition collections."""
    try:
        logger.info("Calling ListCollections...")
        response = rekognition.list_collections()
        logger.info(f"ListCollections raw response: {json.dumps(response, indent=2)}")
        collections = response.get("CollectionIds", [])
        logger.info(f"Found {len(collections)} collections.")
        return collections
    except ClientError as e:
        error_details = e.response.get("Error", {})
        logger.error(f"Error listing collections: {error_details}", exc_info=True)
        raise


def search_faces_by_image(image_bytes: bytes, collection_id: str = DEFAULT_COLLECTION_ID, face_match_threshold: float = 90.0, max_faces: int = 1):
    """Search for faces in the collection using an image."""
    try:
        # Prepare parameters for the API call
        params = {
            'CollectionId': collection_id,
            'Image': {'Bytes': image_bytes},
            'FaceMatchThreshold': face_match_threshold,
            'MaxFaces': max_faces
        }
        
        # Create a log-safe version of the parameters (without the large image byte string)
        params_to_log = params.copy()
        params_to_log['Image'] = f"<bytes of size {len(image_bytes)}>"
        
        logger.info(f"Calling SearchFacesByImage with params: {json.dumps(params_to_log, indent=2)}")

        response = rekognition.search_faces_by_image(**params)
        
        # Log the full raw response for debugging
        logger.info(f"SearchFacesByImage raw response: {json.dumps(response, indent=2, default=str)}")

        if response and response.get("FaceMatches"):
            face_matches = response['FaceMatches']
            logger.info(f"Rekognition found {len(face_matches)} matching face(s) in collection '{collection_id}'.")
            for match in face_matches:
                face = match.get('Face', {})
                similarity = match.get('Similarity')
                face_id = face.get('FaceId')
                if face_id and similarity is not None:
                    logger.info(f"  - Match Details: FaceId={face_id}, Similarity={similarity:.2f}%")
        return response
    except ClientError as e:
        error_details = e.response.get("Error", {})
        if error_details.get('Code') == 'InvalidParameterException' and "no faces in the image" in error_details.get('Message', ''):
            logger.info("Rekognition confirmed no face in image for searching. This is a valid outcome.")
            return None
        else:
            logger.error(f"Error searching faces in collection '{collection_id}': {error_details}", exc_info=True)
            raise


def index_faces(image_bytes: bytes, collection_id: str = DEFAULT_COLLECTION_ID, max_faces: int = 1):
    """Index faces in an image to the collection."""
    try:
        # Prepare parameters for the API call
        params = {
            'CollectionId': collection_id,
            'Image': {'Bytes': image_bytes},
            'MaxFaces': max_faces,
            'DetectionAttributes': ['DEFAULT'],
            # --- THIS IS THE KEY CHANGE ---
            # Tell Rekognition to index faces even if they are low quality.
            'QualityFilter': 'NONE' 
        }

        # Create a log-safe version of the parameters
        params_to_log = params.copy()
        params_to_log['Image'] = f"<bytes of size {len(image_bytes)}>"
        
        logger.info(f"Calling IndexFaces with params: {json.dumps(params_to_log, indent=2)}")

        response = rekognition.index_faces(**params)
        
        # Log the full raw response for debugging
        logger.info(f"IndexFaces raw response: {json.dumps(response, indent=2, default=str)}")

        # The rest of your function can remain the same...
        if response and response.get("FaceRecords"):
            face_records = response['FaceRecords']
            logger.info(f"Rekognition indexed {len(face_records)} face(s) into collection '{collection_id}'.")
            for record in face_records:
                face = record.get('Face', {})
                face_id = face.get('FaceId')
                confidence = face.get('Confidence')
                if face_id and confidence is not None:
                    logger.info(f"  - Indexed Face Details: FaceId={face_id}, Detection Confidence={confidence:.2f}%")
        return response
    except ClientError as e:
        error_details = e.response.get("Error", {})
        if error_details.get('Code') == 'InvalidParameterException' and "no faces in the image" in error_details.get('Message', ''):
            logger.info("Rekognition confirmed no face in image for indexing. This is a valid outcome.")
            return None
        else:
            logger.error(f"Error indexing faces into collection '{collection_id}': {error_details}", exc_info=True)
            raise


def process_face_search_and_index(image_bytes: bytes, collection_id: str = DEFAULT_COLLECTION_ID) -> dict:
    """
    Process an image by first searching for existing faces, then indexing if no match found.
    Returns a dictionary with processing status and face info.
    """
    try:
        # First, try to search for existing faces. We ask for up to 10 faces.
        search_response = search_faces_by_image(image_bytes, collection_id, max_faces=10)

        if search_response:
            face_matches = search_response.get("FaceMatches", [])
            if face_matches:
                logger.info(f"Face MATCHED. Processing the best of {len(face_matches)} match(es).")
                bbox_data = search_response.get("SearchedFaceBoundingBox")
                matched_face_data = face_matches[0]["Face"]
                face_info = FaceInfo(
                    FaceId=matched_face_data.get("FaceId"),
                    BoundingBox=BoundingBox(**bbox_data),
                    ImageId=matched_face_data.get("ImageId"),
                    Confidence=matched_face_data.get("Confidence")
                )
                return {"status": "matched", "face_info": face_info}

        # No match found, try to index as new face
        logger.info("No match found. Attempting to index new face(s).")
        index_response = index_faces(image_bytes, collection_id, max_faces=10)

        if index_response:
            face_records = index_response.get('FaceRecords', [])
            if face_records:
                logger.info(f"New face(s) INDEXED. Processing the first of {len(face_records)} indexed face(s).")
                face = face_records[0]['Face']
                bbox = face.get("BoundingBox", {})
                face_info = FaceInfo(
                    FaceId=face.get("FaceId"),
                    BoundingBox=BoundingBox(**bbox),
                    ImageId=face.get("ImageId"),
                    Confidence=face.get("Confidence", 0.0)
                )
                return {"status": "indexed", "face_info": face_info}
            
            # --- NEW LOGIC BLOCK ---
            # Check if a face was detected but deemed too low quality to index.
            unindexed_faces = index_response.get('UnindexedFaces', [])
            if unindexed_faces:
                reasons = [face.get('Reasons') for face in unindexed_faces]
                logger.warning(f"A face was detected but NOT indexed due to low quality. Reasons: {reasons}")
                return {"status": "low_quality_face", "face_info": None}
            # --- END NEW LOGIC BLOCK ---

        # If both search and index operations result in no detectable faces (or no usable faces)
        logger.warning("No face could be detected in the image for either search or index.")
        return {"status": "no_face", "face_info": None}

    except Exception as e:
        logger.error(f"Unhandled error in processing face search and index: {e}", exc_info=True)
        return {"status": "error", "face_info": None, "error_message": str(e)}