from fastapi import APIRouter, Response, Query
from typing import Optional
from app.services.avigilon_api import *
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger("avigilon-endpoints")

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
async def get_events_subtopics():
    resp = await get_events_subtopics_service()
    if resp:
        return Response(content=resp.text, status_code=resp.status_code, media_type=resp.headers.get("content-type", "application/json"))
    else:
        return Response(content="{}", status_code=503, media_type="application/json")

@router.get("/api/appearance-descriptions", response_class=Response)
async def get_appearance_descriptions():
    resp = await get_appearance_descriptions_service()
    if resp:
        return Response(content=resp.text, status_code=resp.status_code, media_type=resp.headers.get("content-type", "application/json"))
    else:
        return Response(content="{}", status_code=503, media_type="application/json")