import logging
from fastapi import APIRouter, Response, Request
from app.services.appearance_api import search_appearance_service, search_by_description_service

router = APIRouter()
logger = logging.getLogger("avigilon-appearance-events")

@router.post("/api/appearance-search", response_class=Response)
async def appearance_search(request: Request):
    body = await request.json()
    from_time = body.get("from")
    to_time = body.get("to")
    appearances = body.get("appearances")
    camera_ids = body.get("cameraIds")
    limit = body.get("limit", 100)
    scan_type = body.get("scanType", "FULL")
    token = body.get("token")
    resp = await search_appearance_service(
        from_time=from_time,
        to_time=to_time,
        appearances=appearances,
        camera_ids=camera_ids,
        limit=limit,
        scan_type=scan_type,
        token=token
    )
    if resp:
        return Response(content=resp.text, status_code=resp.status_code, media_type="application/json")
    else:
        return Response(content="{}", status_code=503, media_type="application/json")

@router.post("/api/appearance-search-by-description", response_class=Response)
async def appearance_search_by_description(request: Request):
    body = await request.json()
    from_time = body.get("from")
    to_time = body.get("to")
    query_descriptors = body.get("queryDescriptors")
    camera_ids = body.get("cameraIds")
    limit = body.get("limit", 100)
    scan_type = body.get("scanType", "FULL")
    token = body.get("token")
    resp = await search_by_description_service(
        from_time=from_time,
        to_time=to_time,
        query_descriptors=query_descriptors,
        camera_ids=camera_ids,
        limit=limit,
        scan_type=scan_type,
        token=token
    )
    if resp:
        return Response(content=resp.text, status_code=resp.status_code, media_type="application/json")
    else:
        return Response(content="{}", status_code=503, media_type="application/json")
