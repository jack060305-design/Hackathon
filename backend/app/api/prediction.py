from fastapi import APIRouter, HTTPException
from datetime import datetime
from ..schemas import RiskPredictionRequest, RiskPredictionResponse
from ..models import risk_model
from ..services.florida_counties import florida_counties

router = APIRouter()

@router.post("/predict", response_model=RiskPredictionResponse)
async def predict_risk(request: RiskPredictionRequest):
    try:
        risk_score = risk_model.predict(
            request.wind_speed,
            request.rainfall,
            request.population_density
        )

        if risk_score >= 0.7:
            risk_level = "High"
            recommendations = ["Immediate action required", "Prepare evacuation", "Secure property"]
        elif risk_score >= 0.4:
            risk_level = "Medium"
            recommendations = ["Prepare supplies", "Stay informed", "Review evacuation routes"]
        else:
            risk_level = "Low"
            recommendations = ["Monitor updates", "Keep emergency kit ready"]

        return RiskPredictionResponse(
            county=request.county,
            risk_score=risk_score,
            risk_level=risk_level,
            recommendations=recommendations,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/counties")
async def get_county_list():
    counties = await florida_counties.get_all_counties()
    return {"counties": counties}


@router.get("/county-map")
async def get_county_map_data():
    """All 67 counties with lat/lon + evacuation tier for mapping."""
    return {"counties": florida_counties.get_county_map_points()}
