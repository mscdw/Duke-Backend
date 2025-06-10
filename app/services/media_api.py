import httpx
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
verify_ssl = settings.AVIGILON_API_VERIFY_SSL
AVIGILON_BASE = settings.AVIGILON_BASE
logger = get_logger("avigilon-media-service")

async def get_media_service(camera_id, t, format):
    url = f"{AVIGILON_BASE}/media"
    params = {
        "session": settings.SESSION_TOKEN,
        "cameraId": camera_id,
        "t": t,
        "format": format
    }
    if format == "json":
        params["media"] = "meta"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.get(url, params=params)
            return resp
    except httpx.RequestError as exc:
        logger.error(f"Fetch media failed: {exc}")
        return None
