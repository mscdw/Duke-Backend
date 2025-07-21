import boto3
from botocore.exceptions import ClientError
from app.models.aws_models import FaceInfo, BoundingBox
from app.core.logging import get_logger

logger = get_logger("aws-services")

DEFAULT_COLLECTION_ID = 'new-face-collection-2'
rekognition = boto3.client("rekognition", region_name="us-east-2")


def create_collection(collection_id: str = DEFAULT_COLLECTION_ID):
    """Create a new Rekognition collection."""
    try:
        response = rekognition.create_collection(CollectionId=collection_id)
        logger.info(f"CreateCollection response: {response}")
        return response
    except ClientError as e:
        logger.error(f"Error creating collection {collection_id}: {e}")
        raise


def list_collections():
    """List all Rekognition collections."""
    try:
        response = rekognition.list_collections()
        collections = response.get("CollectionIds", [])
        logger.info(f"Collections: {collections}")
        return collections
    except ClientError as e:
        logger.error(f"Error listing collections: {e}")
        raise


def search_faces_by_image(image_bytes: bytes, collection_id: str = DEFAULT_COLLECTION_ID, face_match_threshold: float = 90.0, max_faces: int = 1):
    """Search for faces in the collection using an image."""
    try:
        response = rekognition.search_faces_by_image(
            CollectionId=collection_id,
            Image={'Bytes': image_bytes},
            FaceMatchThreshold=face_match_threshold,
            MaxFaces=max_faces
        )
        return response
    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidParameterException' and "no faces in the image" in e.response['Error']['Message']:
            logger.info("Rekognition confirmed no face in image. This is a valid outcome.")
            return None
        else:
            logger.error(f"Error searching faces: {e}")
            raise


def index_faces(image_bytes: bytes, collection_id: str = DEFAULT_COLLECTION_ID, max_faces: int = 1):
    """Index faces in an image to the collection."""
    try:
        response = rekognition.index_faces(
            CollectionId=collection_id,
            Image={'Bytes': image_bytes},
            MaxFaces=max_faces
        )
        return response
    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidParameterException' and "no faces in the image" in e.response['Error']['Message']:
            logger.info("Rekognition confirmed no face in image for indexing. This is a valid outcome.")
            return None
        else:
            logger.error(f"Error indexing faces: {e}")
            raise


def process_face_search_and_index(image_bytes: bytes, collection_id: str = DEFAULT_COLLECTION_ID) -> dict:
    """
    Process an image by first searching for existing faces, then indexing if no match found.
    Returns a dictionary with processing status and face info.
    """
    try:
        # First, try to search for existing faces
        search_response = search_faces_by_image(image_bytes, collection_id)

        if search_response:
            face_matches = search_response.get("FaceMatches", [])
            if face_matches:
                logger.info("Face MATCHED in collection")
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
        logger.info("No match found. Indexing as new face.")
        index_response = index_faces(image_bytes, collection_id)

        if index_response:
            face_records = index_response.get('FaceRecords') or []
            if face_records:
                logger.info("New face INDEXED successfully")
                face = face_records[0]['Face']
                bbox = face.get("BoundingBox", {})
                face_info = FaceInfo(
                    FaceId=face.get("FaceId"),
                    BoundingBox=BoundingBox(**bbox),
                    ImageId=face.get("ImageId"),
                    Confidence=face.get("Confidence", 0.0)
                )
                return {"status": "indexed", "face_info": face_info}

        # No face detected in image
        logger.warning("No face could be detected in the image")
        return {"status": "no_face", "face_info": None}

    except Exception as e:
        logger.error(f"Error processing face search and index: {e}", exc_info=True)
        return {"status": "error", "face_info": None, "error_message": str(e)}