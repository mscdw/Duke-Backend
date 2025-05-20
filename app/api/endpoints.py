import logging
from fastapi import APIRouter, Request, Response, Query
from typing import Optional
import httpx
from app.core.config import get_settings

router = APIRouter()
logger = logging.getLogger("avigilon-endpoints")
settings = get_settings()
verify_ssl = settings.AVIGILON_API_VERIFY_SSL
AVIGILON_BASE_URL = "https://10.89.26.169:8443/mt/api/rest/v1"

@router.get("/api/health", response_class=Response)
async def health_check():
    url = f"{AVIGILON_BASE_URL}/health"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=5) as client:
            resp = await client.get(url)
            logger.info(f"Health check status: {resp.status_code}")
            return Response(content=resp.text, status_code=resp.status_code, media_type=resp.headers.get("content-type", "text/plain"))
    except httpx.RequestError as exc:
        logger.error(f"Health check failed: {exc}")
        return Response(content="DOWN", status_code=503, media_type="text/plain")

@router.get("/api/web-capabilities", response_class=Response)
async def web_capabilities():
    url = f"{AVIGILON_BASE_URL}/wep-capabilities"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=5) as client:
            resp = await client.get(url)
            return Response(content=resp.text, status_code=resp.status_code, media_type=resp.headers.get("content-type", "application/json"))
    except httpx.RequestError as exc:
        logger.error(f"Web capabilities failed: {exc}")
        return Response(content="{}", status_code=503, media_type="application/json")

@router.get("/api/cameras", response_class=Response)
async def get_cameras():
    url = f"{AVIGILON_BASE_URL}/cameras?session={settings.SESSION_TOKEN}"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.get(url)
            return Response(content=resp.text, status_code=resp.status_code, media_type=resp.headers.get("content-type", "application/json"))
    except httpx.RequestError as exc:
        logger.error(f"Get cameras failed: {exc}")
        return Response(content="{}", status_code=503, media_type="application/json")

@router.get("/api/sites", response_class=Response)
async def get_sites():
    url = f"{AVIGILON_BASE_URL}/sites?session={settings.SESSION_TOKEN}"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.get(url)
            return Response(content=resp.text, status_code=resp.status_code, media_type=resp.headers.get("content-type", "application/json"))
    except httpx.RequestError as exc:
        logger.error(f"Get sites failed: {exc}")
        return Response(content="{}", status_code=503, media_type="application/json")

@router.get("/api/site", response_class=Response)
async def get_site(id: Optional[str] = Query(None), ):
    url = f"{AVIGILON_BASE_URL}/site?session={settings.SESSION_TOKEN}" + (f"&id={id}" if id else "")
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.get(url)
            return Response(content=resp.text, status_code=resp.status_code, media_type=resp.headers.get("content-type", "application/json"))
    except httpx.RequestError as exc:
        logger.error(f"Get site failed: {exc}")
        return Response(content="{}", status_code=503, media_type="application/json")

@router.get("/api/servers", response_class=Response)
async def get_servers():
    url = f"{AVIGILON_BASE_URL}/server/ids?session={settings.SESSION_TOKEN}"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.get(url)
            return Response(content=resp.text, status_code=resp.status_code, media_type=resp.headers.get("content-type", "application/json"))
    except httpx.RequestError as exc:
        logger.error(f"Get servers failed: {exc}")
        return Response(content="{}", status_code=503, media_type="application/json")

@router.get("/api/event-subtopics", response_class=Response)
async def get_events():
    url = f"{AVIGILON_BASE_URL}/event-subtopics"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.get(url)
            return Response(content=resp.text, status_code=resp.status_code, media_type=resp.headers.get("content-type", "application/json"))
    except httpx.RequestError as exc:
        logger.error(f"Get events subtopics failed: {exc}")
        return Response(content="{}", status_code=503, media_type="application/json")

@router.get("/api/events")
async def get_recent_events(serverId: str = Query(...), queryType:str = Query(...) ):
    url = f"{AVIGILON_BASE_URL}/events/search?session={settings.SESSION_TOKEN}&limit=10&serverId={serverId}&queryType={queryType}"
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.get(url)
            return Response(content=resp.text, status_code=resp.status_code, media_type=resp.headers.get("content-type", "application/json"))
    except httpx.RequestError as exc:
        logger.error(f"Fetch events failed: {exc}")
        return Response(content="{}", status_code=503, media_type="application/json")

@router.post("/api/media", response_class=Response)
async def post_media(request: Request, cameraId: Optional[str] = Query(None), format: Optional[str] = Query(None), t: Optional[str] = Query(None), ):
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
        body = await request.body()
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
            resp = await client.post(url, content=body)
            return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type", "application/octet-stream"))
    except httpx.RequestError as exc:
        logger.error(f"Post media failed: {exc}")
        return Response(content=b"", status_code=503, media_type="application/octet-stream")
