import httpx
import logging
from app.core.config import get_settings

settings = get_settings()
verify_ssl = settings.AVIGILON_API_VERIFY_SSL
AVIGILON_BASE_URL = "https://10.89.26.169:8443/mt/api/rest/v1"
logger = logging.getLogger("avigilon-service")

async def get_media_service(camera_id, t, format):
    url = f"{AVIGILON_BASE_URL}/media"
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
