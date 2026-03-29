import httpx
from typing import List, Dict

async def fetch_hurricanes() -> List[Dict]:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://www.nhc.noaa.gov/CurrentStorms.json",
                timeout=10.0
            )
            if response.status_code != 200:
                return []
            data = response.json()
            return data.get("activeStorms") or data.get("active_storms") or []
        except:
            return [{"name": "No active storms", "category": "None"}]
