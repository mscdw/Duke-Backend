import httpx
import logging
from app.core.config import get_settings

settings = get_settings()
verify_ssl = settings.AVIGILON_API_VERIFY_SSL
AVIGILON_BASE_URL = "https://10.89.26.169:8443/mt/api/rest/v1"
logger = logging.getLogger("avigilon-service")

async def health_check_service():
    url = f"{AVIGILON_BASE_URL}/health"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=5) as client:
            resp = await client.get(url)
            return resp
    except httpx.RequestError as exc:
        logger.error(f"Health check failed: {exc}")
        return None

async def web_capabilities_service():
    url = f"{AVIGILON_BASE_URL}/wep-capabilities"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=5) as client:
            resp = await client.get(url)
            return resp
    except httpx.RequestError as exc:
        logger.error(f"Web capabilities failed: {exc}")
        return None

async def get_cameras_service():
    url = f"{AVIGILON_BASE_URL}/cameras?session={settings.SESSION_TOKEN}"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.get(url)
            return resp
    except httpx.RequestError as exc:
        logger.error(f"Get cameras failed: {exc}")
        return None

async def get_sites_service():
    url = f"{AVIGILON_BASE_URL}/sites?session={settings.SESSION_TOKEN}"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.get(url)
            return resp
    except httpx.RequestError as exc:
        logger.error(f"Get sites failed: {exc}")
        return None

async def get_site_service(id=None):
    url = f"{AVIGILON_BASE_URL}/site?session={settings.SESSION_TOKEN}" + (f"&id={id}" if id else "")
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.get(url)
            return resp
    except httpx.RequestError as exc:
        logger.error(f"Get site failed: {exc}")
        return None

async def get_servers_service():
    url = f"{AVIGILON_BASE_URL}/server/ids?session={settings.SESSION_TOKEN}"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.get(url)
            return resp
    except httpx.RequestError as exc:
        logger.error(f"Get servers failed: {exc}")
        return None

async def get_events_service():
    url = f"{AVIGILON_BASE_URL}/event-subtopics"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.get(url)
            return resp
    except httpx.RequestError as exc:
        logger.error(f"Get events subtopics failed: {exc}")
        return None

async def get_active_events_service(serverId):
    url = f"{AVIGILON_BASE_URL}/events/search?session={settings.SESSION_TOKEN}&limit=10&serverId={serverId}&queryType=ACTIVE"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.get(url)
            return resp
    except httpx.RequestError as exc:
        logger.error(f"Fetch events failed: {exc}")
        return None

async def post_media_service(body, cameraId=None, format=None, t=None):
    params = [f"session={settings.SESSION_TOKEN}"]
    if cameraId:
        params.append(f"cameraId={cameraId}")
    if format:
        params.append(f"format={format}")
    if t:
        params.append(f"t={t}")
    query_str = "&".join(params)
    url = f"{AVIGILON_BASE_URL}/media?{query_str}"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.post(url, content=body)
            return resp
    except httpx.RequestError as exc:
        logger.error(f"Post media failed: {exc}")
        return None

async def search_events_service(from_time, to_time, server_id, limit=5, event_topics="ALL"):
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
