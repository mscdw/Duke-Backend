from fastapi import APIRouter, Response, Query
from fastapi.responses import JSONResponse
from app.services.appearance_api import search_appearance_service, search_by_description_service, fetch_all_face_events
from pydantic import BaseModel
from typing import Optional, List, Dict
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger("avigilon-appearance-events")

class AppearanceSearchBody(BaseModel):
    from_time: Optional[str] = None
    to_time: Optional[str] = None
    appearances: Optional[Dict] = None
    cameraIds: Optional[List] = None
    limit: Optional[int] = 100
    scanType: Optional[str] = "FULL"
    token: Optional[str] = None

class AppearanceSearchByDescriptionBody(BaseModel):
    from_time: Optional[str] = None
    to_time: Optional[str] = None
    queryDescriptors: Optional[List] = None
    cameraIds: Optional[List] = None
    limit: Optional[int] = 100
    scanType: Optional[str] = "FULL"
    token: Optional[str] = None

@router.post("/api/appearance-search", response_class=Response)
async def appearance_search(body: AppearanceSearchBody):
    resp = await search_appearance_service(
        from_time=body.from_time,
        to_time=body.to_time,
        appearances=body.appearances,
        camera_ids=body.cameraIds,
        limit=body.limit,
        scan_type=body.scanType,
        token=body.token
    )
    if resp:
        return Response(content=resp.text, status_code=resp.status_code, media_type="application/json")
    else:
        return Response(content="{}", status_code=503, media_type="application/json")

@router.post("/api/appearance-search-by-description", response_class=Response)
async def appearance_search_by_description(body: AppearanceSearchByDescriptionBody):
    resp = await search_by_description_service(
        from_time=body.from_time,
        to_time=body.to_time,
        query_descriptors=body.queryDescriptors,
        camera_ids=body.cameraIds,
        limit=body.limit,
        scan_type=body.scanType,
        token=body.token
    )
    if resp:
        return Response(content=resp.text, status_code=resp.status_code, media_type="application/json")
    else:
        return Response(content="{}", status_code=503, media_type="application/json")

@router.get("/api/all-face-events-fetch", response_class=JSONResponse)
async def all_face_events_fetch(
    from_time: str = Query(..., description="Start time in ISO format, e.g. 2024-06-10T00:00:00.000Z"),
    to_time: str = Query(..., description="End time in ISO format, e.g. 2024-06-10T00:00:00.000Z")
):
    result = await fetch_all_face_events(from_time, to_time)
    return JSONResponse(content=result)
