from pydantic import BaseModel
from typing import List, Optional

class RiskPredictionRequest(BaseModel):
    county: str
    wind_speed: float
    rainfall: float
    population_density: str

class RiskPredictionResponse(BaseModel):
    county: str
    risk_score: float
    risk_level: str
    recommendations: List[str]
    timestamp: str

class DisasterEvent(BaseModel):
    id: str
    event_type: str
    magnitude: Optional[float]
    location: str
    coordinates: List[float]
    timestamp: str
