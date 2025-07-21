import asyncio
import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.events_api import fetch_and_yield_event_pages

logger = get_logger("generic-events-scheduler")
settings = get_settings()

central_base_url = settings.CENTRAL_BASE
post_endpoint = "/store-events"
post_url = f"{central_base_url.rstrip('/')}{post_endpoint}"

# This now defines the page size for both fetching from the source API
# and for posting to the storage endpoint.
API_PAGE_SIZE = 1000
verify_ssl = settings.AVIGILON_API_VERIFY_SSL


def generic_events_fetch_job():
    async def fetch_and_post_logic():
        to_time_dt = datetime.now(timezone.utc)
        # Using a large time delta for backfilling. Adjust as needed.
        from_time_dt = to_time_dt - timedelta(days=7)
        from_time = from_time_dt.isoformat().replace("+00:00", "Z")
        to_time = to_time_dt.isoformat().replace("+00:00", "Z")

        total_posted_count = 0
        total_failed_pages = 0
        page_number = 0

        logger.info(
            f"Starting memory-efficient event processing from {from_time} to {to_time}..."
        )

        try:
            # Create a single client to be reused for all POST requests.
            async with httpx.AsyncClient(verify=verify_ssl, timeout=300) as client:
                # The 'async for' loop consumes the async generator page by page.
                async for event_page in fetch_and_yield_event_pages(
                    from_time, to_time, page_size=API_PAGE_SIZE
                ):
                    page_number += 1
                    
                    if not event_page:
                        logger.warning(f"Received empty page {page_number}, skipping.")
                        continue

                    logger.info(
                        f"Posting page {page_number} with {len(event_page)} events..."
                    )

                    try:
                        # Post the currently fetched page immediately.
                        response = await client.post(
                            post_url, json={"events": event_page}
                        )
                        response.raise_for_status()

                        # Get count from the response for accurate tracking.
                        response_data = response.json()
                        stored_in_page = response_data.get("stored_count", len(event_page))
                        total_posted_count += stored_in_page

                        logger.info(
                            f"Successfully posted page {page_number}. Stored {stored_in_page} events."
                        )

                    except httpx.HTTPStatusError as exc:
                        total_failed_pages += 1
                        logger.error(
                            f"HTTP error posting page {page_number}: {exc.response.status_code} - "
                            f"Response: {exc.response.text}"
                        )
                    except Exception as e:
                        total_failed_pages += 1
                        logger.error(
                            f"An unexpected error occurred while posting page {page_number}: {e}",
                            exc_info=True,
                        )

            # --- Final Summary Report ---
            logger.info("--- Event Processing Summary ---")
            if page_number == 0:
                logger.info("No event pages were found in the given time range.")
            else:
                logger.info(
                    f"Processed {page_number} page(s) in total. "
                    f"Successfully stored approximately {total_posted_count} events."
                )
                if total_failed_pages > 0:
                    logger.warning(
                        f"Number of failed pages: {total_failed_pages}. Some events were not stored."
                    )

        except Exception as e:
            logger.error(
                f"A critical unhandled error occurred during the event processing job: {e}",
                exc_info=True,
            )

    # Run the asynchronous logic from the synchronous APScheduler job.
    asyncio.run(fetch_and_post_logic())


def start_generic_events_scheduler():
    # scheduler = BackgroundScheduler(timezone="UTC")
    # scheduler.add_job(
    #     generic_events_fetch_job,
    #     "interval",
    #     minutes=1440,
    #     next_run_time=datetime.now(timezone.utc),
    #     misfire_grace_time=300,  # Increased grace time for longer-running jobs
    # )
    # scheduler.start()
    # logger.info("Generic events scheduler started (runs every 60 minutes).")
    pass
