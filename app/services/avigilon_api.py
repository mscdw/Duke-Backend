import httpx
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
verify_ssl = settings.AVIGILON_API_VERIFY_SSL
AVIGILON_BASE = settings.AVIGILON_BASE
logger = get_logger("avigilon-service")

async def health_check_service():
    url = f"{AVIGILON_BASE}/health"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=5) as client:
            resp = await client.get(url)
            return resp
    except httpx.RequestError as exc:
        logger.error(f"Health check failed: {exc}")
        return None

async def web_capabilities_service():
    url = f"{AVIGILON_BASE}/wep-capabilities"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=5) as client:
            resp = await client.get(url)
            return resp
    except httpx.RequestError as exc:
        logger.error(f"Web capabilities failed: {exc}")
        return None

async def get_cameras_service():
    url = f"{AVIGILON_BASE}/cameras?session={settings.SESSION_TOKEN}"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.get(url)
            return resp
    except httpx.RequestError as exc:
        logger.error(f"Get cameras failed: {exc}")
        return None

async def get_sites_service():
    url = f"{AVIGILON_BASE}/sites?session={settings.SESSION_TOKEN}"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.get(url)
            return resp
    except httpx.RequestError as exc:
        logger.error(f"Get sites failed: {exc}")
        return None

async def get_site_service(id=None):
    url = f"{AVIGILON_BASE}/site?session={settings.SESSION_TOKEN}" + (f"&id={id}" if id else "")
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.get(url)
            return resp
    except httpx.RequestError as exc:
        logger.error(f"Get site failed: {exc}")
        return None

async def get_servers_service():
    url = f"{AVIGILON_BASE}/server/ids?session={settings.SESSION_TOKEN}"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.get(url)
            return resp
    except httpx.RequestError as exc:
        logger.error(f"Get servers failed: {exc}")
        return None

async def get_events_subtopics_service():
    url = f"{AVIGILON_BASE}/event-subtopics"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.get(url)
            return resp
    except httpx.RequestError as exc:
        logger.error(f"Get events subtopics failed: {exc}")
        return None

async def get_appearance_descriptions_service():
    url = f"{AVIGILON_BASE}/appearance/descriptions?session={settings.SESSION_TOKEN}"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.get(url)
            return resp
    except httpx.RequestError as exc:
        logger.error(f"Get appearance descriptions failed: {exc}")
        return None

