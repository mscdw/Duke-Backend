import asyncio
import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta, timezone, date as date_obj
import json
import base64
import uuid
import boto3
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.appearance_api import fetch_all_face_events
from app.services.avigilon_api import get_servers_service

logger = get_logger("generic-events-scheduler")
settings = get_settings()

# --- S3 Configuration ---
# NOTE: Ensure your environment has AWS credentials configured (e.g., via IAM role or env vars)
# and that the S3_FACE_IMAGE_BUCKET is defined in your settings.
try:
    s3_client = boto3.client("s3")
    S3_BUCKET_NAME = settings.S3_FACE_IMAGE_BUCKET
except Exception as e:
    logger.error(f"Failed to initialize S3 client or get bucket name: {e}. Face image uploads will fail.", exc_info=True)
    s3_client = None
    S3_BUCKET_NAME = None

central_base_url = settings.CENTRAL_BASE
post_endpoint = "/store-events"
latest_ts_endpoint = "/events/latest-timestamp"
post_url = f"{central_base_url.rstrip('/')}{post_endpoint}"

# --- URL Definitions ---
latest_ts_url = f"{central_base_url.rstrip('/')}{latest_ts_endpoint}"
latest_face_ts_url = f"{latest_ts_url}?type=CUSTOM_APPEARANCE"


API_PAGE_SIZE = 100
verify_ssl = settings.AVIGILON_API_VERIFY_SSL
DEFAULT_BACKFILL_DAYS = 30

# --- NEW: Helper for Token-Based Pagination ---
# NOTE: This function is designed to work with an Avigilon-like /events/search API.
# It would ideally be placed in a dedicated service file (e.g., app/services/events_api.py).
async def fetch_events_with_token_pagination(client: httpx.AsyncClient, server_id: str, from_time: str, to_time: str, limit: int):
    """
    Asynchronously fetches events from a source API using token-based pagination.

    Yields:
        A list of event dictionaries per page.
    """
    # This assumes the base URL for the source (e.g., Avigilon) API is configured in settings.
    # The session/auth headers are assumed to be handled by the httpx.AsyncClient instance.
    source_api_base_url = getattr(settings, "AVIGILON_BASE", "")
    if not source_api_base_url:
        logger.error("AVIGILON_BASE setting is not configured. Cannot fetch generic events.")
        return

    search_endpoint = "/events/search" # As per the provided documentation
    url = f"{source_api_base_url.rstrip('/')}{search_endpoint}"

    params = {
        "serverId": server_id,
        "session": settings.SESSION_TOKEN,
        "queryType": "TIME_RANGE",
        "from": from_time,
        "to": to_time,
        "limit": limit
    }
    page_num = 0

    while True:
        page_num += 1
        try:
            logger.debug(f"Fetching event page {page_num} from source API with params: {params}")
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            # Correctly parse the nested JSON structure. The 'events' list and
            # pagination 'token' are located inside the 'result' object.
            result_data = data.get("result", {})
            events = result_data.get("events", [])
            if events:
                yield events

            token = result_data.get("token")
            if token:
                # For the next request, we need the token, the correct queryType, and the session.
                params = {
                    "session": settings.SESSION_TOKEN,
                    "queryType": "CONTINUE",
                    "token": token,
                    # NOTE: Per API behavior, 'serverId' is not allowed on continuation requests.
                }
            else:
                logger.info(f"No more pagination tokens found. Fetched a total of {page_num} page(s).")
                break
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error on page {page_num} while fetching events from source API: {e.response.status_code} - {e.response.text}")
            break
        except Exception as e:
            logger.error(f"Error fetching event page {page_num} from source API: {e}", exc_info=True)
            break


def generic_events_fetch_job():
    """
    Fetches new generic events since the last run using efficient,
    token-based pagination and posts them to the central API.
    """
    async def fetch_and_post_logic():
        logger.info("--- Starting GENERIC event processing job ---")

        # 1. Get Server ID first. This is required for all event searches.
        server_id = None
        try:
            # NOTE: This assumes a single-server setup. For multi-server, this logic would need expansion.
            servers_resp = await get_servers_service()
            if not (servers_resp and servers_resp.status_code == 200):
                logger.error(f"Failed to fetch servers to determine server ID. Status: {servers_resp.status_code if servers_resp else 'N/A'}. Aborting job.")
                return

            servers_data = servers_resp.json()
            servers_list = servers_data.get("result", {}).get("servers", [])
            
            if not servers_list:
                logger.error("No sites/servers found in the API response. Cannot fetch generic events. Aborting job.")
                return

            # 2. Get the first server dictionary from the list and then extract its 'id'.
            #    Using .get("id") is safer than ['id'] as it won't raise a KeyError.
            server_id = servers_list[0].get("id")
            if not server_id:
                logger.error("First server found has no ID. Cannot fetch generic events. Aborting job.")
                return
            logger.info(f"Found server ID: {server_id}. Proceeding with event fetch.")
        except Exception as e:
            logger.error(f"A critical error occurred while fetching server ID: {e}. Aborting job.", exc_info=True)
            return

        # 2. Determine the time window to process based on the last stored event.
        from_time_dt: datetime
        try:
            # Check for a manual backfill start time override via environment variable
            manual_start_time_str = getattr(settings, "GENERIC_BACKFILL_START_TIME", None)
            if manual_start_time_str:
                from_time_dt = datetime.fromisoformat(manual_start_time_str)
                logger.warning(f"MANUAL OVERRIDE: Using GENERIC_BACKFILL_START_TIME: {from_time_dt.isoformat()}")
            else:
                async with httpx.AsyncClient(verify=verify_ssl, timeout=60) as client:
                    response = await client.get(latest_ts_url)
                    response.raise_for_status()
                    data = response.json()
                    latest_timestamp_str = data.get("latest_timestamp")

                    if latest_timestamp_str:
                        # Start from the timestamp of the last known event.
                        from_time_dt = datetime.fromisoformat(latest_timestamp_str.replace("Z", "+00:00"))
                        logger.info(f"Last processed event timestamp found: {from_time_dt.isoformat()}. Fetching new events since then.")
                    else:
                        # No data found, perform initial backfill.
                        from_time_dt = datetime.now(timezone.utc) - timedelta(days=DEFAULT_BACKFILL_DAYS)
                        logger.info(f"No previous generic events found. Starting backfill from: {from_time_dt.isoformat()}")
        except Exception as e:
            logger.error(f"Could not determine start time for GENERIC events: {e}. Aborting job.", exc_info=True)
            return

        to_time_dt = datetime.now(timezone.utc)

        # Add a 1ms buffer to prevent re-fetching the very last event if the source API's 'from' is inclusive.
        from_time_dt_buffered = from_time_dt + timedelta(milliseconds=1)

        if from_time_dt_buffered >= to_time_dt:
            logger.info("System is already up-to-date. No new time window to process for generic events.")
            return

        from_time_iso = from_time_dt_buffered.isoformat().replace("+00:00", "Z")
        to_time_iso = to_time_dt.isoformat().replace("+00:00", "Z")

        total_posted_count, total_failed_pages, page_number = 0, 0, 0
        logger.info(f"Processing generic events for time window: {from_time_iso} to {to_time_iso}")
        try:
            async with httpx.AsyncClient(verify=verify_ssl, timeout=300) as client:
                async for event_page in fetch_events_with_token_pagination(client, server_id, from_time_iso, to_time_iso, limit=API_PAGE_SIZE):
                    page_number += 1
                    if not event_page: continue
                    logger.info(f"Posting page {page_number} with {len(event_page)} generic events...")
                    try:
                        post_response = await client.post(post_url, json={"events": event_page})
                        post_response.raise_for_status()
                        response_data = post_response.json()
                        stored_in_page = response_data.get("stored_count", len(event_page))
                        total_posted_count += stored_in_page
                        logger.info(f"Successfully posted page {page_number}. Stored {stored_in_page} generic events.")
                    except httpx.HTTPStatusError as exc:
                        total_failed_pages += 1
                        logger.error(f"HTTP error posting page {page_number} of generic events: {exc.response.status_code} - Response: {exc.response.text}")
                    except Exception as e:
                        total_failed_pages += 1
                        logger.error(f"An unexpected error occurred while posting page {page_number} of generic events: {e}", exc_info=True)
            logger.info("--- Generic Event Processing Summary for this Run ---")
            if page_number == 0:
                logger.info("No new generic events were found for the processed time window.")
            else:
                logger.info(f"Processed {page_number} page(s). Stored a total of {total_posted_count} generic events.")
                if total_failed_pages > 0:
                    logger.warning(f"Number of failed pages: {total_failed_pages}. These pages were not stored.")
        except Exception as e:
            logger.error(f"A critical unhandled error occurred during the generic event processing job: {e}", exc_info=True)
    asyncio.run(fetch_and_post_logic())


# --- S3 Image Upload Helper ---
async def upload_face_image_to_s3(base64_image_data: str, event_timestamp: str) -> str | None:
    """
    Decodes a base64 image, uploads it to S3, and returns the S3 object key.

    Args:
        base64_image_data: The base64-encoded image string.
        event_timestamp: The ISO format timestamp of the event for path generation.

    Returns:
        The S3 object key if successful, otherwise None.
    """
    if not all([s3_client, S3_BUCKET_NAME, base64_image_data, event_timestamp]):
        logger.warning("S3 upload skipped due to missing client, bucket, or data.")
        return None

    try:
        # Create a structured path based on the event time
        dt_obj = datetime.fromisoformat(event_timestamp.replace("Z", "+00:00"))
        s3_key = (
            f"faces/{dt_obj.year}/{dt_obj.month:02d}/{dt_obj.day:02d}/"
            f"{dt_obj.strftime('%H-%M-%S')}-{uuid.uuid4()}.jpg"
        )

        # Decode the base64 string. It might contain a data URI header.
        if "," in base64_image_data:
            _header, encoded = base64_image_data.split(",", 1)
        else:
            encoded = base64_image_data

        image_data = base64.b64decode(encoded)

        # Upload to S3. boto3's s3 client methods are synchronous, so we run in an executor.
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: s3_client.put_object(Bucket=S3_BUCKET_NAME, Key=s3_key, Body=image_data, ContentType="image/jpeg"),
        )
        logger.debug(f"Successfully uploaded image to S3: {s3_key}")
        return s3_key
    except (ClientError, base64.binascii.Error, Exception) as e:
        logger.error(f"Failed to upload image to S3 for event at {event_timestamp}: {e}", exc_info=True)
        return None


# --- CORRECTED FACE EVENTS JOB ---

async def face_events_logic():
    logger.info("--- STARTING ROBUST FACE EVENTS JOB ---")
    # 1. Determine the starting day ONCE at the beginning of the job.
    try:
        # Check for a manual backfill start date override via environment variable
        manual_start_date_str = getattr(settings, "FACE_BACKFILL_START_DATE", None)
        if manual_start_date_str:
            # Expecting ISO date format like "YYYY-MM-DD"
            current_day_to_process = date_obj.fromisoformat(manual_start_date_str)
            logger.warning(f"MANUAL OVERRIDE: Using FACE_BACKFILL_START_DATE. Starting process from: {current_day_to_process}")
        else:
            async with httpx.AsyncClient(verify=verify_ssl, timeout=60) as client:
                response = await client.get(latest_face_ts_url)
                response.raise_for_status()
                latest_timestamp_str = response.json().get("latest_timestamp")
                
                if latest_timestamp_str:
                    latest_event_date = datetime.fromisoformat(latest_timestamp_str.replace("Z", "+00:00")).date()
                    current_day_to_process = latest_event_date + timedelta(days=1)
                    logger.info(f"Last processed day was {latest_event_date}. Starting process from: {current_day_to_process}")
                else:
                    current_day_to_process = datetime.now(timezone.utc).date() - timedelta(days=DEFAULT_BACKFILL_DAYS)
                    logger.info(f"No previous data found. Starting backfill from: {current_day_to_process}")
    except Exception as e:
        logger.error(f"Could not determine start day from API. Aborting job: {e}", exc_info=True)
        return

    # 2. Loop through days until we are caught up.
    today = datetime.now(timezone.utc).date()
    while current_day_to_process < today:
        logger.info(f"--- Processing day: {current_day_to_process} ---")
        
        from_time_dt = datetime(current_day_to_process.year, current_day_to_process.month, current_day_to_process.day, 0, 0, 0, tzinfo=timezone.utc)
        to_time_dt = datetime(current_day_to_process.year, current_day_to_process.month, current_day_to_process.day, 23, 59, 59, tzinfo=timezone.utc)
        from_time = from_time_dt.isoformat().replace("+00:00", "Z")
        to_time = to_time_dt.isoformat().replace("+00:00", "Z")

        try:
            payload = await fetch_all_face_events(from_time, to_time)
            appearances = payload.get("results") or payload.get("appearances", [])

            if not appearances:
                logger.info(f"Day {current_day_to_process} was empty. Advancing to the next day.")
                current_day_to_process += timedelta(days=1)
                continue

            logger.info(f"Found {len(appearances)} events for {current_day_to_process}. Transforming, uploading images, and posting.")

            events_to_post = []
            for appearance in appearances:
                if not isinstance(appearance, dict):
                    continue

                # Pop the base64 image to be replaced by an S3 key.
                # Assuming the field is 'faceImage'. This may need to be adjusted.
                base64_image = appearance.pop("faceImage", None)
                event_timestamp = appearance.get("eventStartTime")

                if base64_image and event_timestamp:
                    s3_key = await upload_face_image_to_s3(base64_image, event_timestamp)
                    if s3_key:
                        # Add the S3 key to the event payload
                        appearance["s3ImageKey"] = s3_key
                    else:
                        # If upload fails, we skip this event to avoid storing incomplete data.
                        logger.warning(f"Skipping event {appearance.get('id')} for timestamp {event_timestamp} due to S3 upload failure.")
                        continue

                # Standardize event fields
                appearance["type"] = "CUSTOM_APPEARANCE"
                appearance["timestamp"] = event_timestamp
                appearance["cameraId"] = appearance.get("cameraId")
                appearance["originatingServerId"] = appearance.get("originatingServerId")
                appearance["originatingEventId"] = appearance.get("id", 1)
                appearance["thisId"] = appearance.get("id", 1)
                events_to_post.append(appearance)

            if not events_to_post:
                logger.warning(f"Transformation and S3 upload for {current_day_to_process} resulted in 0 events to post. Advancing to next day.")
                current_day_to_process += timedelta(days=1)
                continue

            async with httpx.AsyncClient(verify=verify_ssl, timeout=600) as client:
                response = await client.post(post_url, json={"events": events_to_post})
                response.raise_for_status()
                stored_count = response.json().get("stored_count", len(events_to_post))
                logger.info(f"Successfully posted {stored_count} face events for {current_day_to_process}.")

            # IMPORTANT: After finding and posting data, break the loop.
            # The next scheduled job run will pick up from this new state.
            logger.info("Data found and posted for this run. The scheduler will continue from here on the next run.")
            break 
        
        except Exception as e:
            logger.error(f"Failed to process day {current_day_to_process}: {e}. Aborting job run.", exc_info=True)
            return # Exit if any single day has a critical failure

    logger.info("Face events job finished. System is now caught up.")


def face_events_fetch_job():
    """
    Synchronous wrapper that calls the robust, self-advancing logic.
    """
    asyncio.run(face_events_logic())


def start_event_schedulers():
    """
    (This function is correct and remains unchanged, but includes a helpful
     suggestion for speeding up the initial backfill)
    """
    scheduler = BackgroundScheduler(timezone="UTC")
    
    scheduler.add_job(
        generic_events_fetch_job,
        "interval",
        minutes=1,
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=10),
        misfire_grace_time=600,
        id="generic_events_job"
    )
    
    # SUGGESTION: To speed up the initial 30-day backfill, temporarily change
    # the schedule below to run every few minutes. Once caught up, revert it
    # to the daily 'cron' schedule.
    scheduler.add_job(
        face_events_fetch_job,
        'interval',  # Use 'interval' for fast backfilling. Change to 'cron' for normal operation.
        minutes=1,   # Run every 5 minutes.
        # cron schedule for normal operation (once caught up):
        # 'cron',
        # hour=0,
        # minute=30,
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=20),
        misfire_grace_time=600,
        id="face_events_job"
    )
    
    scheduler.start()
    logger.info("Unified event schedulers started.")
    logger.info("-> Generic events job runs hourly.")
    logger.info("-> Face events job is set to run every 5 minutes for backfilling.")
    # pass