import asyncio
import httpx
from typing import List, Dict, Any, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone

# --- S3 Integration Imports ---
import boto3
from botocore.exceptions import ClientError
import base64 # Still needed for error handling, but not primary path

from app.core.logging import get_logger
from app.core.config import get_settings
# Assuming this service returns an object with FaceId and a model_dump method
from app.services.aws_services import process_all_faces_in_image

logger = get_logger("event-facial-recognition-scheduler")
settings = get_settings()

# --- S3 Configuration ---
try:
    s3_client = boto3.client("s3")
    S3_BUCKET_NAME = settings.S3_FACE_IMAGE_BUCKET
except Exception as e:
    logger.error(f"Failed to initialize S3 client or get bucket name: {e}. S3 downloads will fail.", exc_info=True)
    s3_client = None
    S3_BUCKET_NAME = None

central_base_url = settings.CENTRAL_BASE
verify_ssl = settings.AVIGILON_API_VERIFY_SSL
# Using relative paths is fine if base_url is set on the client
fetch_url = f"{central_base_url.rstrip('/')}/events/for-recognition"
update_url = f"{central_base_url.rstrip('/')}/events/with-recognition"
FETCH_LIMIT = 10  # Recognition is intensive; use a smaller batch size.

async def download_media_from_s3(s3_key: str) -> Optional[bytes]:
    """Downloads image bytes from S3 given an object key."""
    if not all([s3_client, S3_BUCKET_NAME, s3_key]):
        logger.warning("S3 download skipped due to missing client, bucket, or key.")
        return None
    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None, lambda: s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        )
        return response["Body"].read()
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            logger.error(f"S3 object not found with key: {s3_key}")
        else:
            logger.error(f"Failed to download from S3 with key {s3_key}: {e}", exc_info=True)
        return None

async def process_events_for_facial_recognition_job():
    """The main job function that orchestrates fetching, processing, and updating."""
    logger.info("Starting facial recognition job for events...")
    total_processed_count = 0

    if not s3_client:
        logger.error("S3 client not available. Aborting facial recognition job.")
        return
    try:
        async with httpx.AsyncClient(base_url=central_base_url, verify=verify_ssl, timeout=120) as client:
            while True:
                updates_to_send: List[Dict[str, Any]] = []

                logger.info(f"Fetching next batch of up to {FETCH_LIMIT} events...")
                fetch_response = await client.get(fetch_url, params={"limit": FETCH_LIMIT})
                fetch_response.raise_for_status()
                events_to_process = fetch_response.json().get("events", [])

                if not events_to_process:
                    logger.info("No new events found. The job has processed all available records.")
                    break

                batch_size = len(events_to_process)
                logger.info(f"Found {batch_size} events in this batch. Processing...")

                for event in events_to_process:
                    event_id = event.get("_id")
                    s3_key = event.get("s3ImageKey")

                    if not event_id or not s3_key:
                        logger.warning(f"Skipping event due to missing '_id' or 's3ImageKey'.")
                        continue

                    try:
                        image_bytes = await download_media_from_s3(s3_key)

                        if not image_bytes:
                            logger.error(f"Could not download image from S3 for event {event_id} (key: {s3_key}). Skipping.")
                            # Consider marking this event as failed in the DB to avoid retries.
                            continue

                        # --- THIS IS THE MAIN LOGIC CHANGE ---
                        # 1. Call the new function which returns a list of results
                        list_of_face_results = process_all_faces_in_image(image_bytes)
                        
                        # 2. Build the final update payload using the new model structure
                        update_payload = {
                            "eventId": event_id,
                            "processed_at": datetime.now(timezone.utc).isoformat(),
                            "detected_faces": list_of_face_results  # Assign the whole list here
                        }
                        
                        updates_to_send.append(update_payload)
                        logger.info(f"Prepared update for event {event_id} with {len(list_of_face_results)} detected face(s).")
                        # --- END OF LOGIC CHANGE ---

                    except Exception as e:
                        logger.error(f"Critical error processing image for event {event_id}: {e}", exc_info=True)
                        # Create a payload that still matches the model, but indicates a top-level error
                        error_payload = {
                             "eventId": event_id,
                             "processed_at": datetime.now(timezone.utc).isoformat(),
                             "detected_faces": [{
                                 "status": "error",
                                 "error_message": f"Scheduler-side error during AWS processing: {str(e)}"
                             }]
                        }
                        updates_to_send.append(error_payload)

                if updates_to_send:
                    logger.info(f"Sending {len(updates_to_send)} facial recognition updates to central for this batch.")
                    update_response = await client.post(update_url, json={"updates": updates_to_send})
                    if update_response.status_code >= 400:
                         logger.error(f"HTTP Error {update_response.status_code} posting updates. Response: {update_response.text}")
                    update_response.raise_for_status()
                    updated_count = update_response.json().get("updated_count", 0)
                    total_processed_count += updated_count
                    logger.info(f"Successfully posted updates for batch. Central reported {updated_count} events updated.")

                # Break if we processed the last available batch
                if len(events_to_process) < FETCH_LIMIT:
                    logger.info("Processed the last available batch of events.")
                    break

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error during facial recognition job: {e.response.status_code} - {e.response.text}", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred in the facial recognition scheduler: {e}", exc_info=True)

    finally:
        logger.info(f"Facial recognition job finished. Total events processed in this run: {total_processed_count}.")


def run_async_facial_recognition_job():
    """
    This is the synchronous wrapper function. Its only job is to create an
    event loop and run our main async function until it's complete.
    """
    try:
        asyncio.run(process_events_for_facial_recognition_job())
    except Exception:
        logger.error("The async job runner for facial recognition crashed.", exc_info=True)


def start_event_facial_recognition_scheduler():
    # """Initializes and starts the background scheduler."""
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        run_async_facial_recognition_job,  # Point the scheduler to our new synchronous wrapper
        "interval",
        minutes=1, # Run every 5 minutes to keep up
        next_run_time=datetime.now(timezone.utc),
        misfire_grace_time=300, # 5 minutes
    )
    scheduler.start()
    logger.info("Event facial recognition scheduler started (runs every 5 minutes).")
