import asyncio
import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta, timezone, date as date_obj

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.avigilon_api import get_servers_service

logger = get_logger("generic-events-scheduler")
settings = get_settings()

# --- Constants for Appearance Search ---
FACET_GENDER = "GENDER"
TAG_MALE = "MALE"
TAG_FEMALE = "FEMALE"

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

# --- Helpers for Token-Based Pagination ---
# NOTE: These functions are designed to work with Avigilon-like APIs.
# They would ideally be placed in a dedicated service file (e.g., app/services/events_api.py).
async def fetch_events_with_token_pagination(client: httpx.AsyncClient, server_id: str, from_time: str, to_time: str, limit: int):
    """
    Asynchronously fetches events from a source API using token-based pagination.

    Yields:
        A list of event dictionaries per page.
    """
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


async def fetch_appearances_with_token_pagination(client: httpx.AsyncClient, query_descriptors: list, from_time: str, to_time: str, limit: int):
    """
    Asynchronously fetches appearance events from a source API using token-based pagination.
    This uses search-by-description to get all male and female appearances.

    Yields:
        A list of appearance event dictionaries per page.
    """
    source_api_base_url = getattr(settings, "AVIGILON_BASE", "")
    if not source_api_base_url:
        logger.error("AVIGILON_BASE setting is not configured. Cannot fetch appearance events.")
        return

    search_endpoint = "/appearance/search-by-description" # The target endpoint
    url = f"{source_api_base_url.rstrip('/')}{search_endpoint}"

    # The /appearance/search-by-description endpoint uses a POST request with a JSON body.
    json_payload = {
        "session": settings.SESSION_TOKEN,
        "queryType": "TIME_RANGE",
        "queryDescriptors": query_descriptors,
        "from": from_time,
        "to": to_time,
        "limit": limit,
        "scanType": "FULL"
    }
    page_num = 0
    gender_tag = query_descriptors[0].get('tag', 'UNKNOWN')

    while True:
        page_num += 1
        try:
            logger.debug(f"Fetching appearance page {page_num} for {gender_tag} from source API with payload: {json_payload}")
            response = await client.post(url, json=json_payload)
            response.raise_for_status()
            data = response.json()

            # The response structure is assumed to be {"result": {"results": [...], "token": "..."}}
            result_data = data.get("result", {})
            appearances = result_data.get("results", [])
            if appearances:
                yield appearances

            token = result_data.get("token")
            if token:
                # For the next request, use the token.
                json_payload = {
                    "session": settings.SESSION_TOKEN,
                    "queryType": "CONTINUE",
                    "token": token,
                }
            else:
                logger.info(f"No more pagination tokens for appearances for {gender_tag}. Fetched a total of {page_num} page(s).")
                break
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error on page {page_num} while fetching appearances for {gender_tag} from source API: {e.response.status_code} - {e.response.text}")
            break
        except Exception as e:
            logger.error(f"Error fetching appearance page {page_num} for {gender_tag} from source API: {e}", exc_info=True)
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


# --- FACE EVENTS JOB ---

async def face_events_fetch_and_post_logic():
    """
    Fetches new face appearance events since the last run, standardizes them,
    and posts them to the central API. Media enrichment and facial recognition
    are handled by downstream schedulers.
    """
    logger.info("--- Starting FACE event processing job ---")

    # 1. Get Server ID first. This will be used for enriching the event payload.
    server_id = None
    try:
        servers_resp = await get_servers_service()
        if not (servers_resp and servers_resp.status_code == 200):
            logger.error(f"Failed to fetch servers to determine server ID. Status: {servers_resp.status_code if servers_resp else 'N/A'}. Aborting job.")
            return

        servers_data = servers_resp.json()
        servers_list = servers_data.get("result", {}).get("servers", [])
        
        if not servers_list:
            logger.error("No sites/servers found in the API response. Cannot fetch face events. Aborting job.")
            return

        server_id = servers_list[0].get("id")
        if not server_id:
            logger.error("First server found has no ID. Cannot fetch face events. Aborting job.")
            return
        logger.info(f"Found server ID: {server_id}. Proceeding with face event fetch.")
    except Exception as e:
        logger.error(f"A critical error occurred while fetching server ID: {e}. Aborting job.", exc_info=True)
        return

    # 2. Determine the time window to process based on the last stored event.
    from_time_dt: datetime
    try:
        manual_start_time_str = getattr(settings, "FACE_BACKFILL_START_TIME", None)
        if manual_start_time_str:
            from_time_dt = datetime.fromisoformat(manual_start_time_str)
            logger.warning(f"MANUAL OVERRIDE: Using FACE_BACKFILL_START_TIME: {from_time_dt.isoformat()}")
        else:
            async with httpx.AsyncClient(verify=verify_ssl, timeout=60) as client:
                response = await client.get(latest_face_ts_url)
                response.raise_for_status()
                data = response.json()
                latest_timestamp_str = data.get("latest_timestamp")

                if latest_timestamp_str:
                    from_time_dt = datetime.fromisoformat(latest_timestamp_str.replace("Z", "+00:00"))
                    logger.info(f"Last processed face event timestamp found: {from_time_dt.isoformat()}. Fetching new events since then.")
                else:
                    from_time_dt = datetime.now(timezone.utc) - timedelta(days=DEFAULT_BACKFILL_DAYS)
                    logger.info(f"No previous face events found. Starting backfill from: {from_time_dt.isoformat()}")
    except Exception as e:
        logger.error(f"Could not determine start time for FACE events: {e}. Aborting job.", exc_info=True)
        return

    to_time_dt = datetime.now(timezone.utc)
    from_time_dt_buffered = from_time_dt + timedelta(milliseconds=1)

    if from_time_dt_buffered >= to_time_dt:
        logger.info("System is already up-to-date. No new time window to process for face events.")
        return

    from_time_iso = from_time_dt_buffered.isoformat().replace("+00:00", "Z")
    to_time_iso = to_time_dt.isoformat().replace("+00:00", "Z")

    total_posted_count, total_failed_pages, total_pages_processed = 0, 0, 0
    logger.info(f"Processing face events for time window: {from_time_iso} to {to_time_iso}")

    # Define the descriptors for male and female searches to get all human appearances
    gender_descriptors = [
        [{"facet": FACET_GENDER, "tag": TAG_MALE}],
        [{"facet": FACET_GENDER, "tag": TAG_FEMALE}]
    ]

    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=300) as client:
            for descriptors in gender_descriptors:
                gender_tag = descriptors[0]['tag']
                logger.info(f"--- Starting fetch for GENDER: {gender_tag} ---")
                page_number = 0
                async for appearance_page in fetch_appearances_with_token_pagination(client, descriptors, from_time_iso, to_time_iso, limit=API_PAGE_SIZE):
                    page_number += 1
                    total_pages_processed += 1
                    if not appearance_page: continue

                    events_to_post = []
                    for appearance in appearance_page:
                        if not isinstance(appearance, dict): continue

                        # The raw appearance event from the source API uses 'timestamp' for the event time.
                        # We must use this key and then standardize the payload for our system.
                        event_timestamp = appearance.get("timestamp")
                        if not event_timestamp:
                            logger.warning(f"Skipping appearance with no 'timestamp' field: {appearance.get('id')}")
                            continue

                        # Standardize event fields for consistent storage, similar to other services.
                        # We also rename 'deviceGid' to 'cameraId' for downstream compatibility.
                        appearance["type"] = "CUSTOM_APPEARANCE"
                        appearance["timestamp"] = event_timestamp
                        appearance["eventStartTime"] = event_timestamp # Add for consistency
                        appearance["originatingServerId"] = server_id
                        appearance["originatingEventId"] = server_id # Per request
                        appearance["thisId"] = server_id # Temp hack for index TODO review
                        appearance["cameraId"] = appearance.pop("deviceGid", None) # Rename for media enrichment
                        events_to_post.append(appearance)

                    if not events_to_post:
                        logger.warning(f"Page {page_number} for {gender_tag} resulted in 0 events to post after transformation.")
                        continue

                    logger.info(f"Posting page {page_number} with {len(events_to_post)} {gender_tag} face events...")
                    try:
                        post_response = await client.post(post_url, json={"events": events_to_post})
                        post_response.raise_for_status()
                        # If the post was successful (2xx), we assume all events were accepted.
                        # This makes logging more robust against a potentially incorrect `stored_count`
                        # from the downstream API, ensuring our logs reflect the number of events
                        # we successfully transmitted.
                        stored_in_page = len(events_to_post)
                        total_posted_count += stored_in_page
                        logger.info(f"Successfully posted page {page_number} for {gender_tag}. Stored {stored_in_page} face events.")
                    except httpx.HTTPStatusError as exc:
                        total_failed_pages += 1
                        logger.error(f"HTTP error posting page {page_number} of {gender_tag} face events: {exc.response.status_code} - Response: {exc.response.text}")
                    except Exception as e:
                        total_failed_pages += 1
                        logger.error(f"An unexpected error occurred while posting page {page_number} of {gender_tag} face events: {e}", exc_info=True)
                logger.info(f"--- Finished fetch for GENDER: {gender_tag}. Processed {page_number} page(s). ---")
        
        logger.info("--- Face Event Processing Summary for this Run ---")
        if total_pages_processed == 0:
            logger.info("No new face events were found for the processed time window.")
        else:
            logger.info(f"Processed {total_pages_processed} page(s) in total. Stored a total of {total_posted_count} face events.")
            if total_failed_pages > 0:
                logger.warning(f"Number of failed pages: {total_failed_pages}. These pages were not stored.")
    except Exception as e:
        logger.error(f"A critical unhandled error occurred during the face event processing job: {e}", exc_info=True)


def face_events_fetch_job():
    """
    Synchronous wrapper that calls the async face event fetching logic.
    """
    asyncio.run(face_events_fetch_and_post_logic())


def start_event_schedulers():
    """
    Initializes and starts the background schedulers for fetching generic
    and face events.
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
    
    # The face events job runs frequently to ensure new appearances are
    # ingested quickly for near real-time processing by downstream schedulers.
    scheduler.add_job(
        face_events_fetch_job,
        'interval',
        minutes=1,
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=20),
        misfire_grace_time=600,
        id="face_events_job"
    )
    
    scheduler.start()
    logger.info("Unified event schedulers started.")
    logger.info(f"-> Generic events job runs every 1 minute(s).")
    logger.info(f"-> Face events job runs every 1 minute(s).")