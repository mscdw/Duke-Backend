import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from app.services.auth import authenticate
from app.core.logging import get_logger

logger = get_logger("auth-scheduler")

def auth_token_refresh_job():
    async def refresh_logic():
        try:
            logger.info(f"Refreshing Avigilon API session token at {datetime.now().isoformat()} UTC...")
            await authenticate()
            logger.info("Session token refreshed successfully.")
        except Exception as e:
            logger.error(f"Failed to refresh session token: {e}")
    asyncio.run(refresh_logic())

def start_auth_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(auth_token_refresh_job, 'cron', minute=0, timezone='UTC')
    scheduler.start()
    logger.info("Auth token refresh scheduler started (runs every hour at minute 0 UTC)")
