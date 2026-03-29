import httpx
from typing import List
from ..schemas import DisasterEvent

async def fetch_earthquakes(limit: int = 10) -> List[DisasterEvent]:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://earthquake.usgs.gov/fdsnws/event/1/query",
            params={
                "format": "geojson",
                "latitude": 27.8,
                "longitude": -81.5,
                "maxradiuskm": 500,
                "minmagnitude": 2.0,
                "limit": limit
            },
            timeout=10.0
        )

        if response.status_code != 200:
            return []

        data = response.json()
        events = []

        for feature in data.get("features", []):
            props = feature.get("properties", {})
            geometry = feature.get("geometry", {})
            coords = geometry.get("coordinates", [0, 0, 0])

            events.append(DisasterEvent(
                id=props.get("id", ""),
                event_type="earthquake",
                magnitude=props.get("mag"),
                location=props.get("place", "Unknown"),
                coordinates=[coords[1], coords[0]],
                timestamp=props.get("time", "")
            ))

        return events[:limit]
