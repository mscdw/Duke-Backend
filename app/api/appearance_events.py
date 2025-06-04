import logging
from fastapi import APIRouter, Response, Query
from fastapi.responses import JSONResponse
from app.services.appearance_api import search_appearance_service, search_by_description_service
from app.services.avigilon_api import get_cameras_service
from pydantic import BaseModel
from typing import Optional, List, Dict

router = APIRouter()
logger = logging.getLogger("avigilon-appearance-events")

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
async def all_face_events_fetch(date: str = Query(..., description="Date in YYYY-MM-DD format")):
    from_time = f"{date}T00:00:00.000Z"
    to_time = f"{date}T23:59:59.999Z"
    cameras_resp = await get_cameras_service()
    cameras_data = cameras_resp.json()
    camera_ids = [cam["id"] for cam in cameras_data.get("result", []).get("cameras", []) if "id" in cam]
    query_descriptors = [
        {"facet": "FACE_MASK_PRESENCE", "tag": "NOT_DETECTED"},
        {"facet": "FACE_MASK_PRESENCE", "tag": "DETECTED"}
    ]
    flat_results = []
    token = None
    resp = await search_by_description_service(
        from_time=from_time,
        to_time=to_time,
        query_descriptors=query_descriptors,
        camera_ids=camera_ids,
        limit=100
    )
    while resp and resp.status_code == 200:
        data = resp.json()
        results = data.get("result", {}).get("results", [])
        token = data.get("result", {}).get("token", None)
        for item in results:
            flat_item = item.copy()
            flat_item["cameraId"] = flat_item.pop("deviceGid")
            flat_item["eventStartTime"] = flat_item.pop("timestamp")
            flat_item["eventEndTime"] = flat_item.pop("endTimestamp")
            snapshots = flat_item.pop("snapshots", [])
            for snap in snapshots:
                if snap.get("type") == "APPEARANCE_SEARCH_SNAPSHOT_TYPE_FACE":
                    snap_flat = flat_item.copy()
                    snap_flat["eventTimestamp"] = snap["timestamp"]
                    flat_results.append(snap_flat)
        if token:
            resp = await search_by_description_service(token=token)
        else:
            break
    total_length = len(flat_results)
    return JSONResponse(content={"total_length": total_length, "results": flat_results})
