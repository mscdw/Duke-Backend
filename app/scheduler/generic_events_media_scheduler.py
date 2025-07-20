import asyncio
import httpx
import base64
from typing import List, Dict, Any, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.media_api import get_media_service

logger = get_logger("generic-events-media-scheduler")
settings = get_settings()

central_base_url = settings.CENTRAL_BASE
verify_ssl = settings.AVIGILON_API_VERIFY_SSL

# --- API Endpoints for the Central Application ---
# NOTE: These endpoints must be created in your central application.
# 1. GETs events that need their media field populated.
EVENTS_FOR_ENRICHMENT_URL = f"{central_base_url.rstrip('/')}/events-for-enrichment"
# 2. PATCHes/POSTs events with the new media data.
UPDATE_EVENTS_MEDIA_URL = f"{central_base_url.rstrip('/')}/events/media"

# --- Configuration ---
TARGET_EVENT_TYPE = "DEVICE_CLASSIFIED_OBJECT_MOTION_START"
BATCH_SIZE = 50  # How many events to fetch and process in a single batch.
IMAGE_FORMAT = "jpeg"


async def _fetch_and_encode_media(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Fetches media for a single event and returns an update payload."""
    event_id = event.get("id")
    camera_id = event.get("cameraId")
    timestamp = event.get("eventStartTime")

    if not all([event_id, camera_id, timestamp]):
        logger.warning(f"Skipping event due to missing data needed for media fetch: {event}")
        return None

    media_resp = await get_media_service(camera_id, timestamp, IMAGE_FORMAT)
    if media_resp and media_resp.status_code == 200:
        image_base64 = base64.b64encode(media_resp.content).decode("utf-8")
        return {"eventId": event_id, "imageBaseString": image_base64}

    logger.warning(
        f"Failed to fetch media for event {event_id} (camera {camera_id} at {timestamp}). "
        f"Status: {media_resp.status_code if media_resp else 'N/A'}"
    )
    return None


async def enrich_events_job_logic():
    """The core async logic for the media enrichment job."""
    logger.info("Starting generic event media enrichment job...")
    total_enriched_count = 0

    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=300) as client:
            while True:
                # 1. Fetch a batch of events that need enrichment from your central app
                logger.info(f"Fetching a batch of up to {BATCH_SIZE} events to enrich...")
                try:
                    params = {"type": TARGET_EVENT_TYPE, "limit": BATCH_SIZE}
                    resp = await client.get(EVENTS_FOR_ENRICHMENT_URL, params=params)
                    resp.raise_for_status()
                    events_to_process = resp.json().get("events", [])
                except httpx.RequestError as e:
                    logger.error(f"Could not connect to central app at {EVENTS_FOR_ENRICHMENT_URL}: {e}")
                    break
                except httpx.HTTPStatusError as e:
                    logger.error(f"Failed to fetch events for enrichment: {e.response.status_code} - {e.response.text}")
                    break

                if not events_to_process:
                    logger.info("No more events to enrich. Job finished for this run.")
                    break

                logger.info(f"Found {len(events_to_process)} events. Fetching media concurrently...")

                # 2. Concurrently fetch media for the entire batch
                enrichment_tasks = [_fetch_and_encode_media(event) for event in events_to_process]
                update_payloads = await asyncio.gather(*enrichment_tasks)
                valid_updates = [p for p in update_payloads if p is not None]

                if not valid_updates:
                    logger.warning("No media could be fetched for the current batch.")
                    if len(events_to_process) < BATCH_SIZE: break
                    else: continue

                # 3. Post the batch of updates back to the central application
                logger.info(f"Posting {len(valid_updates)} media updates back to the central app...")
                try:
                    update_resp = await client.post(UPDATE_EVENTS_MEDIA_URL, json={"updates": valid_updates})
                    update_resp.raise_for_status()
                    updated_count = update_resp.json().get("updated_count", len(valid_updates))
                    total_enriched_count += updated_count
                    logger.info(f"Successfully updated {updated_count} events with media.")
                except httpx.HTTPStatusError as e:
                    logger.error(f"Failed to post media updates: {e.response.status_code} - {e.response.text}")

                if len(events_to_process) < BATCH_SIZE:
                    logger.info("Processed the last available batch of events.")
                    break
    except Exception as e:
        logger.error(f"A critical unhandled error occurred during the enrichment job: {e}", exc_info=True)

    logger.info(f"--- Media Enrichment Summary ---")
    logger.info(f"Total events enriched in this run: {total_enriched_count}")


def generic_events_media_enrichment_job():
    """Synchronous wrapper for APScheduler."""
    asyncio.run(enrich_events_job_logic())


def start_generic_events_media_scheduler():
    """Starts the background scheduler for the media enrichment job."""
    scheduler = BackgroundScheduler(timezone="UTC")
    # Runs every hour at 10 minutes past the hour, giving the main ingestion job time to complete.
    scheduler.add_job(generic_events_media_enrichment_job, 'cron', minute=10, misfire_grace_time=300)
    scheduler.start()
    logger.info("Generic events media enrichment scheduler started (runs hourly at xx:10).")