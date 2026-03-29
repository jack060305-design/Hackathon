"""
Florida Ocean Disaster API Endpoints
"""

from fastapi import APIRouter, HTTPException
from ..services.florida_ocean_tracker import florida_ocean

router = APIRouter()


@router.get("/active-storms")
async def get_active_storms():
    """Get active storms threatening Florida"""
    storms = await florida_ocean.fetch_active_storms()
    return {"count": len(storms), "storms": storms}


@router.get("/florida-impact/{storm_id}")
async def get_florida_impact(storm_id: str):
    """Get Florida impact prediction"""
    storms = await florida_ocean.fetch_active_storms()
    storm = next((s for s in storms if s.get("id") == storm_id), None)

    if not storm:
        mock_storm = {
            "id": storm_id,
            "name": "Ian",
            "category": 4,
            "wind_speed": 130,
            "latitude": 26.5,
            "longitude": -82.5,
            "direction": 45,
            "speed": 12,
            "pressure": 940,
        }
        return florida_ocean.calculate_florida_impact(mock_storm)

    return florida_ocean.calculate_florida_impact(storm)


@router.get("/seven-day-outlook")
async def get_seven_day_outlook():
    """Hurricanes / tropical cyclones with modeled ETA within ~7 days, inland %, regional risk."""
    return await florida_ocean.get_seven_day_outlook()


@router.get("/coastal-risk")
async def get_coastal_risk():
    """Get overall coastal risk assessment"""
    storms = await florida_ocean.fetch_active_storms()

    if not storms:
        return {
            "status": "No active storms",
            "coastal_risk": "Low",
            "advisory": "No tropical cyclones threatening Florida",
        }

    max_prob = 0
    for storm in storms:
        impact = florida_ocean.calculate_florida_impact(storm)
        max_prob = max(max_prob, impact["landfall_probability"])

    if max_prob > 70:
        risk = "Extreme"
        advisory = "FLORIDA EMERGENCY - Prepare for landfall"
    elif max_prob > 40:
        risk = "High"
        advisory = "Monitor closely - Florida may be impacted"
    else:
        risk = "Moderate"
        advisory = "Watch conditions - Stay informed"

    return {
        "status": f"{len(storms)} active storm(s)",
        "coastal_risk": risk,
        "advisory": advisory,
        "storms": [{"name": s.get("name"), "category": s.get("category")} for s in storms],
    }
