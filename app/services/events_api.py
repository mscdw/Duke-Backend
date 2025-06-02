import httpx
import logging
from app.core.config import get_settings

settings = get_settings()
verify_ssl = settings.AVIGILON_API_VERIFY_SSL
AVIGILON_BASE_URL = "https://10.89.26.170:8443/mt/api/rest/v1"
logger = logging.getLogger("avigilon-events-service")

async def get_active_events_service(server_id, limit):
    url = f"{AVIGILON_BASE_URL}/events/search?session={settings.SESSION_TOKEN}&limit={limit}&serverId={server_id}&queryType=ACTIVE"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.get(url)
            return resp
    except httpx.RequestError as exc:
        logger.error(f"Fetch events failed: {exc}")
        return None
    
async def get_continue_events_service(token):
    url = f"{AVIGILON_BASE_URL}/events/search?session={settings.SESSION_TOKEN}&token={token}&queryType=CONTINUE"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.get(url)
            return resp
    except httpx.RequestError as exc:
        logger.error(f"Fetch events failed: {exc}")
        return None
    
async def search_events_service(from_time, to_time, server_id, limit, event_topics="ALL"):
    url = f"{AVIGILON_BASE_URL}/events/search"
    params = {
        "session": settings.SESSION_TOKEN,
        "queryType": "TIME_RANGE",
        "from": from_time,
        "to": to_time,
        "serverId": server_id,
        "limit": limit,
        "eventTopics": event_topics
    }
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.get(url, params=params)
            return resp
    except httpx.RequestError as exc:
        logger.error(f"Event search failed: {exc}")
        return None

