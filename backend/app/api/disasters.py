from fastapi import APIRouter, HTTPException
from typing import Any, List

from ..services import inland_risk_map as inland_risk_map_service
from ..services import noaa, nws_alerts, usgs
from ..schemas import DisasterEvent

router = APIRouter()


async def _inland_risk_map_payload(limit: int = 40) -> dict[str, Any]:
    """Shared handler for USGS + NWS inland markers (same JSON as MCP `get_inland_risk_map_json`)."""
    try:
        return await inland_risk_map_service.fetch_inland_risk_markers(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usgs", response_model=List[DisasterEvent])
async def get_usgs_disasters(limit: int = 10):
    try:
        events = await usgs.fetch_earthquakes(limit)
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/noaa/hurricanes")
async def get_noaa_hurricanes():
    try:
        hurricanes = await noaa.fetch_hurricanes()
        return hurricanes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/inland-risk-map",
    operation_id="get_inland_risk_map_under_disasters_hyphen",
)
async def get_inland_risk_map_disasters_hyphen(limit: int = 40):
    return await _inland_risk_map_payload(limit)


@router.get(
    "/inland_risk_map",
    operation_id="get_inland_risk_map_under_disasters_underscore",
)
async def get_inland_risk_map_disasters_underscore(limit: int = 40):
    return await _inland_risk_map_payload(limit)


@router.get("/nws/health")
async def nws_alerts_health() -> dict[str, Any]:
    """
    Diagnostic: same NWS entrypoint as the inland risk map (`alerts/active?area=FL`).
    Use this if you suspect NWS errors — OpenAPI will not list a standalone “NWS” feed otherwise.
    """
    return await nws_alerts.nws_active_alerts_health()
