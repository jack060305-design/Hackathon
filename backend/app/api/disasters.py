from fastapi import APIRouter, HTTPException
from typing import List
from ..services import usgs, noaa
from ..schemas import DisasterEvent

router = APIRouter()

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
