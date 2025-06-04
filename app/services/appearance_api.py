import httpx
import logging
from app.core.config import get_settings
from typing import Optional

settings = get_settings()
verify_ssl = settings.AVIGILON_API_VERIFY_SSL
AVIGILON_BASE = settings.AVIGILON_BASE
logger = logging.getLogger("avigilon-appearance-service")

async def search_appearance_service(
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
    appearances: Optional[dict] = None,
    camera_ids: Optional[list] = None,
    limit: Optional[int] = 100,
    scan_type: Optional[str] = "FULL",
    token: Optional[str] = None
):
    url = f"{AVIGILON_BASE}/appearance/search"
    if token:
        form_data = {
            "session": settings.SESSION_TOKEN,
            "queryType": "CONTINUE",
            "token": token
        }
    else:
        form_data = {
            "session": settings.SESSION_TOKEN,
            "queryType": "TIME_RANGE",
            "appearances": appearances,
            "from": from_time,
            "to": to_time,
            "cameraIds": camera_ids,
            "limit": limit,
            "scanType": scan_type
        }
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.post(url, json=form_data)
            return resp
    except httpx.RequestError as exc:
        logger.error(f"Appearance search failed: {exc}")
        return None

async def search_by_description_service(
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
    query_descriptors: Optional[list] = None,
    camera_ids: Optional[list] = None,
    limit: Optional[int] = 100,
    scan_type: Optional[str] = "FULL",
    token: Optional[str] = None
):
    url = f"{AVIGILON_BASE}/appearance/search-by-description"
    if token:
        form_data = {
            "session": settings.SESSION_TOKEN,
            "queryType": "CONTINUE",
            "token": token
        }
    else:
        form_data = {
            "session": settings.SESSION_TOKEN,
            "queryType": "TIME_RANGE",
            "queryDescriptors": query_descriptors,
            "from": from_time,
            "to": to_time,
            "cameraIds": camera_ids,
            "limit": limit,
            "scanType": scan_type
        }
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.post(url, json=form_data)
            return resp
    except httpx.RequestError as exc:
        logger.error(f"Appearance search-by-description failed: {exc}")
        return None
