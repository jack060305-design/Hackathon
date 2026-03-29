from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import disasters, prediction, ocean
from .api.disasters import _inland_risk_map_payload

app = FastAPI(
    title="Florida Disaster Risk API",
    description=(
        "AI-powered disaster risk prediction for Florida. "
        "**Browser Geolocation** (W3C) is not an HTTP endpoint: the client gets `lat`/`lon` via "
        "`navigator.geolocation`, then may call **`GET /api/disasters/location-context`** with those coordinates."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(disasters.router, prefix="/api/disasters", tags=["disasters"])
app.include_router(prediction.router, prefix="/api/prediction", tags=["prediction"])
app.include_router(ocean.router, prefix="/api/ocean", tags=["ocean"])


@app.get(
    "/api/inland-risk-map",
    tags=["disasters"],
    operation_id="get_inland_risk_map_top_alias",
)
async def get_inland_risk_map_top_alias(limit: int = 40):
    """Short URL alias — same payload as `/api/disasters/inland-risk-map` and MCP `get_inland_risk_map_json`."""
    return await _inland_risk_map_payload(limit)


@app.get("/")
def root():
    return {"message": "Florida Disaster Risk API", "status": "running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
