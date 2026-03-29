import httpx
from typing import List, Dict

async def fetch_hurricanes() -> List[Dict]:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://www.nhc.noaa.gov/index.json",
                timeout=10.0
            )
            if response.status_code != 200:
                return []
            return response.json().get("active_storms", [])
        except:
            return [{"name": "No active storms", "category": "None"}]
