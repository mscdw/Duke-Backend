import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import base64
from app.core.logging import get_logger
from app.services.avigilon_api import get_cameras_service
from app.services.appearance_api import search_by_description_service
from app.services.media_api import get_media_service

logger = get_logger("face-events-scheduler")

def fetch_face_events():
    async def fetch_logic():
        now = datetime.now()
        prev_day = now - timedelta(days=1)
        from_time = prev_day.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'
        to_time = prev_day.replace(hour=23, minute=59, second=59, microsecond=999000).isoformat() + 'Z'
        try:
            logger.info(f"Fetching face events from {from_time} to {to_time} at {now}...")
            cameras_resp = await get_cameras_service()
            cameras_data = cameras_resp.json()
            camera_ids = [cam["id"] for cam in cameras_data.get("result", []).get("cameras", []) if "id" in cam]
            query_descriptors = [
                {"facet": "FACE_MASK_PRESENCE", "tag": "NOT_DETECTED"},
                {"facet": "FACE_MASK_PRESENCE", "tag": "DETECTED"}
            ]
            flat_results = []
            token = None
            resp = await search_by_description_service(
                from_time=from_time,
                to_time=to_time,
                query_descriptors=query_descriptors,
                camera_ids=camera_ids,
                limit=100
            )
            while resp and resp.status_code == 200:
                data = resp.json()
                results = data.get("result", {}).get("results", [])
                token = data.get("result", {}).get("token", None)
                for item in results:
                    flat_item = item.copy()
                    flat_item["cameraId"] = flat_item.pop("deviceGid")
                    flat_item["eventStartTime"] = flat_item.pop("timestamp")
                    flat_item["eventEndTime"] = flat_item.pop("endTimestamp")
                    snapshots = flat_item.pop("snapshots", [])
                    for snap in snapshots:
                        if snap.get("type") == "APPEARANCE_SEARCH_SNAPSHOT_TYPE_FACE":
                            snap_flat = flat_item.copy()
                            snap_flat["eventTimestamp"] = snap["timestamp"]
                            media_resp = await get_media_service(snap_flat["cameraId"], snap["timestamp"], "jpeg")
                            image_base64 = base64.b64encode(media_resp.content).decode("utf-8")
                            snap_flat["imageBaseString"] = image_base64
                            flat_results.append(snap_flat)
                if token:
                    resp = await search_by_description_service(token=token)
                else:
                    break
            total_length = len(flat_results)
            logger.info(f"Fetched {total_length} face events for {from_time} to {to_time}")
        except Exception as e:
            logger.error(f"Error fetching face events: {e}")
    asyncio.run(fetch_logic())

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_face_events, 'cron', hour=1, minute=0, timezone='UTC')
    scheduler.start()
    logger.info("Face events scheduler started (runs daily at 01:00 UTC)")
