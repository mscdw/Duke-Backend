import asyncio
import httpx
import base64
from typing import List, Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.core.config import get_settings
# Assuming this service returns an object with FaceId and a model_dump method
from app.services.aws_services import process_face_search_and_index 

logger = get_logger("event-facial-recognition-scheduler")
settings = get_settings()

central_base_url = settings.CENTRAL_BASE
verify_ssl = settings.AVIGILON_API_VERIFY_SSL
# Using relative paths is fine if base_url is set on the client
fetch_url = f"{central_base_url.rstrip('/')}/events/for-recognition"
update_url = f"{central_base_url.rstrip('/')}/events/with-recognition"
FETCH_LIMIT = 100  # How many events to process per run


async def process_events_for_facial_recognition_job():
    """The main job function that orchestrates fetching, processing, and updating.
    This function will now loop until all available events are processed.
    """
    logger.info("Starting facial recognition job for events...")
    total_processed_count = 0

    try:
        # It's good practice to set base_url on the client
        async with httpx.AsyncClient(base_url=central_base_url, verify=verify_ssl, timeout=120) as client:
            
            # <<< CHANGE: Start a loop to process records in batches >>>
            while True:
                # This list must be cleared for each new batch
                updates_to_send: List[Dict[str, Any]] = []

                # 1. Fetch a batch of events that need processing
                logger.info(f"Fetching next batch of up to {FETCH_LIMIT} events...")
                fetch_response = await client.get(fetch_url, params={"limit": FETCH_LIMIT})
                fetch_response.raise_for_status()
                data = fetch_response.json()
                events_to_process = data.get("events", [])

                # <<< CHANGE: This is now the exit condition for the loop >>>
                if not events_to_process:
                    logger.info("No new events found. The job has processed all available records.")
                    break  # Exit the while loop

                batch_size = len(events_to_process)
                total_processed_count += batch_size
                logger.info(f"Found {batch_size} events in this batch. Processing...")

                # 2. Process each event in the current batch
                for event in events_to_process:
                    event_id = event.get("_id")
                    image_b64 = event.get("imageBaseString")

                    if not event_id or not image_b64:
                        logger.warning(f"Skipping event due to missing '_id' or 'imageBaseString'.")
                        continue

                    try:
                        image_bytes = base64.b64decode(image_b64)

                        processing_result = process_face_search_and_index(image_bytes)
                        status = processing_result.get("status")
                        face_info = processing_result.get("face_info")

                        face_processing_payload = {
                            "processed": True,
                            "processed_at": datetime.now(timezone.utc).isoformat(),
                            "new_face_indexed": False
                        }

                        update_payload = {
                            "eventId": event_id,
                            "personId": None,
                            "personFace": None,
                            "face_processing": face_processing_payload
                        }

                        if status == "matched":
                            face_processing_payload["match_result"] = "matched"
                            update_payload["personId"] = face_info.FaceId
                            update_payload["personFace"] = face_info.model_dump()
                            logger.info(f"Prepared update for event {event_id} with personId {face_info.FaceId} (match_result: matched)")
                        elif status == "indexed":
                            face_processing_payload["match_result"] = "indexed"
                            face_processing_payload["new_face_indexed"] = True
                            update_payload["personId"] = face_info.FaceId
                            update_payload["personFace"] = face_info.model_dump()
                            logger.info(f"Prepared update for event {event_id} with new personId {face_info.FaceId} (match_result: indexed)")
                        elif status == "no_face":
                            face_processing_payload["match_result"] = "no_face"
                            logger.warning(f"No face detected for event {event_id}. (match_result: no_face)")
                        elif status == "error":
                            face_processing_payload["match_result"] = "error"
                            face_processing_payload["error_message"] = processing_result.get("error_message", "Unknown error")
                            logger.error(f"Error processing event {event_id}. (match_result: error)")

                        updates_to_send.append(update_payload)

                    except Exception as e:
                        logger.error(f"Error processing image for event {event_id}: ", exc_info=True)
                        face_processing_payload = {
                            "processed": True, "processed_at": datetime.now(timezone.utc).isoformat(),
                            "match_result": "error", "new_face_indexed": False,
                            "error_message": f"Error in scheduler before Rekognition call: {str(e)}"
                        }
                        updates_to_send.append({"eventId": event_id, "personId": None, "personFace": None, "face_processing": face_processing_payload})

                # 3. Post the results for the current batch
                if updates_to_send:
                    logger.info(f"Sending {len(updates_to_send)} facial recognition updates to central for this batch.")
                    update_response = await client.post(update_url, json={"updates": updates_to_send})
                    update_response.raise_for_status()
                    logger.info(f"Successfully posted updates for batch. Response: {update_response.json()}")

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error during facial recognition job: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        logger.error(f"An unexpected error occurred in the facial recognition scheduler: ", exc_info=True)
    
    finally:
        logger.info(f"Facial recognition job finished. Total events processed in this run: {total_processed_count}.")


# +++ START OF CHANGES +++

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
    """Initializes and starts the background scheduler."""
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        run_async_facial_recognition_job,  # Point the scheduler to our new synchronous wrapper
        'cron',
        hour=3,
        minute=15,
        misfire_grace_time=120,
        next_run_time=datetime.now(timezone.utc)
    )
    scheduler.start()
    logger.info("Event facial recognition scheduler started (runs every day).")

# +++ END OF CHANGES +++