import logging
from fastapi import APIRouter, Response
from app.services.avigilon_api import get_servers_service, get_recent_events_service
import json

router = APIRouter()
logger = logging.getLogger("avigilon-server-events")

@router.get("/api/active-events", response_class=Response)
async def get_active_events_all_servers():
    servers_resp = await get_servers_service()
    if not servers_resp or servers_resp.status_code != 200:
        logger.error(f"Failed to fetch server ids: {e}")
        return Response(content="[]", status_code=503, media_type="application/json")
    try:
        server_ids_json = servers_resp.json()
        server_ids = [server["id"] for server in server_ids_json["result"]["servers"]]
    except Exception as e:
        logger.error(f"Failed to parse server ids: {e}")
        return Response(content="[]", status_code=500, media_type="application/json")
    all_events = {}
    for server_id in server_ids:
        events_resp = await get_recent_events_service(server_id, "ACTIVE")
        if events_resp and events_resp.status_code == 200:
            try:
                events_resp_json = events_resp.json()
                all_events[server_id] = events_resp_json["result"]["events"]
            except Exception as e:
                logger.error(f"Failed to parse events for server {server_id}: {e}")
    return Response(content=json.dumps(all_events), status_code=200, media_type="application/json")

