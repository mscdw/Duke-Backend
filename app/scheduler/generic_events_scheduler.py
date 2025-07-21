import asyncio
import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta, timezone, date as date_obj

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.events_api import fetch_and_yield_event_pages

logger = get_logger("generic-events-scheduler")
settings = get_settings()

central_base_url = settings.CENTRAL_BASE
post_endpoint = "/store-events"
latest_ts_endpoint = "/events/latest-timestamp"
post_url = f"{central_base_url.rstrip('/')}{post_endpoint}"
latest_ts_url = f"{central_base_url.rstrip('/')}{latest_ts_endpoint}"

API_PAGE_SIZE = 100
verify_ssl = settings.AVIGILON_API_VERIFY_SSL
DEFAULT_BACKFILL_DAYS = 7


def generic_events_fetch_job():
    """
    Synchronous wrapper that runs the main async logic for fetching and posting events.
    """
    async def fetch_and_post_logic():
        """
        The core async logic for processing events in complete daily batches.
        """
        # --- START OF NEW DAILY BATCH LOGIC ---
        
        logger.info("Determining the next full day to process...")
        day_to_process: date_obj

        try:
            async with httpx.AsyncClient(verify=verify_ssl, timeout=60) as client:
                response = await client.get(latest_ts_url)
                response.raise_for_status()
                data = response.json()
                latest_timestamp_str = data.get("latest_timestamp")

                if latest_timestamp_str:
                    # A. Database has data. Figure out the next day.
                    latest_event_dt = datetime.fromisoformat(latest_timestamp_str.replace("Z", "+00:00"))
                    latest_event_date = latest_event_dt.date()
                    
                    today = datetime.now(timezone.utc).date()

                    if latest_event_date < today:
                        # We have successfully processed a past day. Move to the next one.
                        day_to_process = latest_event_date + timedelta(days=1)
                        logger.info(f"Last processed day was {latest_event_date}. Processing next full day: {day_to_process}")
                    else:
                        # We are already processing today. Re-process all of today to catch up.
                        day_to_process = today
                        logger.info(f"Already caught up to today. Re-processing all of {day_to_process} to fetch latest events.")
                else:
                    # B. Database is empty. Start the backfill from the beginning.
                    day_to_process = datetime.now(timezone.utc).date() - timedelta(days=DEFAULT_BACKFILL_DAYS)
                    logger.info(f"No previous events found. Starting backfill from day: {day_to_process}")

        except Exception as e:
            logger.error(f"Could not determine start day from API: {e}. Aborting job.", exc_info=True)
            return

        # --- CALCULATE THE FULL DAY FETCH WINDOW ---
        
        # Start of the day to process
        from_time_dt = datetime(
            year=day_to_process.year, month=day_to_process.month, day=day_to_process.day,
            hour=0, minute=0, second=0, tzinfo=timezone.utc
        )

        # End of the day to process
        # If the day is in the past, get the full day. If it's today, get up to now.
        if day_to_process < datetime.now(timezone.utc).date():
            to_time_dt = datetime(
                year=day_to_process.year, month=day_to_process.month, day=day_to_process.day,
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
        else:
            to_time_dt = datetime.now(timezone.utc)
        
        # Convert to Z-formatted strings
        from_time = from_time_dt.isoformat().replace("+00:00", "Z")
        to_time = to_time_dt.isoformat().replace("+00:00", "Z")

        # --- END OF NEW LOGIC ---

        # The rest of the job (fetching and posting) remains the same.
        # It will now operate on the correctly calculated daily window.
        
        total_posted_count, total_failed_pages, page_number = 0, 0, 0
        logger.info(f"Starting event processing for the day window: {from_time} to {to_time}...")

        try:
            async with httpx.AsyncClient(verify=verify_ssl, timeout=300) as client:
                async for event_page in fetch_and_yield_event_pages(from_time, to_time, page_size=API_PAGE_SIZE):
                    page_number += 1
                    if not event_page: continue
                    logger.info(f"Posting page {page_number} with {len(event_page)} events...")
                    try:
                        post_response = await client.post(post_url, json={"events": event_page})
                        post_response.raise_for_status()
                        response_data = post_response.json()
                        stored_in_page = response_data.get("stored_count", len(event_page))
                        total_posted_count += stored_in_page
                        logger.info(f"Successfully posted page {page_number}. Stored {stored_in_page} events.")
                    except httpx.HTTPStatusError as exc:
                        total_failed_pages += 1
                        logger.error(f"HTTP error posting page {page_number}: {exc.response.status_code} - Response: {exc.response.text}")
                    except Exception as e:
                        total_failed_pages += 1
                        logger.error(f"An unexpected error occurred while posting page {page_number}: {e}", exc_info=True)

            logger.info("--- Event Processing Summary for this Run ---")
            if page_number == 0:
                logger.info(f"No new events were found for the processed day: {day_to_process}.")
            else:
                logger.info(f"Processed {page_number} page(s) for day {day_to_process}. Stored {total_posted_count} events.")
                if total_failed_pages > 0:
                    logger.warning(f"Number of failed pages: {total_failed_pages}. These pages for day {day_to_process} were not stored.")

        except Exception as e:
            logger.error(f"A critical unhandled error occurred during the event processing job: {e}", exc_info=True)

    asyncio.run(fetch_and_post_logic())


def start_generic_events_scheduler():
    scheduler = BackgroundScheduler(timezone="UTC")
    # A longer interval is now more appropriate for daily batch processing.
    scheduler.add_job(
        generic_events_fetch_job,
        "interval",
        hours=1, # Run every hour to catch up on "today's" data.
        next_run_time=datetime.now(timezone.utc),
        misfire_grace_time=600, # 10 minutes
    )
    scheduler.start()
    logger.info("Daily batch event scheduler started (runs hourly).")
