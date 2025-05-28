import logging
from fastapi import APIRouter, Request, Response, Query
from typing import Optional
from app.services.avigilon_api import *

router = APIRouter()
logger = logging.getLogger("avigilon-endpoints")

@router.get("/api/health", response_class=Response)
async def health_check():
    resp = await health_check_service()
    if resp:
        return Response(content=resp.text, status_code=resp.status_code, media_type=resp.headers.get("content-type", "text/plain"))
    else:
        return Response(content="DOWN", status_code=503, media_type="text/plain")

@router.get("/api/wep-capabilities", response_class=Response)
async def web_capabilities():
    resp = await web_capabilities_service()
    if resp:
        return Response(content=resp.text, status_code=resp.status_code, media_type=resp.headers.get("content-type", "application/json"))
    else:
        return Response(content="{}", status_code=503, media_type="application/json")

@router.get("/api/cameras", response_class=Response)
async def get_cameras():
    resp = await get_cameras_service()
    if resp:
        return Response(content=resp.text, status_code=resp.status_code, media_type=resp.headers.get("content-type", "application/json"))
    else:
        return Response(content="{}", status_code=503, media_type="application/json")

@router.get("/api/sites", response_class=Response)
async def get_sites():
    resp = await get_sites_service()
    if resp:
        return Response(content=resp.text, status_code=resp.status_code, media_type=resp.headers.get("content-type", "application/json"))
    else:
        return Response(content="{}", status_code=503, media_type="application/json")

@router.get("/api/site", response_class=Response)
async def get_site(id: Optional[str] = Query(None)):
    resp = await get_site_service(id)
    if resp:
        return Response(content=resp.text, status_code=resp.status_code, media_type=resp.headers.get("content-type", "application/json"))
    else:
        return Response(content="{}", status_code=503, media_type="application/json")

@router.get("/api/servers", response_class=Response)
async def get_servers():
    resp = await get_servers_service()
    if resp:
        return Response(content=resp.text, status_code=resp.status_code, media_type=resp.headers.get("content-type", "application/json"))
    else:
        return Response(content="{}", status_code=503, media_type="application/json")

@router.get("/api/event-subtopics", response_class=Response)
async def get_events():
    resp = await get_events_service()
    if resp:
        return Response(content=resp.text, status_code=resp.status_code, media_type=resp.headers.get("content-type", "application/json"))
    else:
        return Response(content="{}", status_code=503, media_type="application/json")