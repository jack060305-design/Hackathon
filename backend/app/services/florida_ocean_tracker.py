"""
Florida Ocean Disaster Tracker
Detects hurricanes/storms and predicts land impact
"""

import httpx
import math
from typing import List, Dict, Any, Optional
from datetime import datetime

from .florida_counties import evacuation_zone, florida_counties

# Approximate centers for Florida sub-regions (outlook risk scoring)
FLORIDA_REGIONS: tuple[dict[str, Any], ...] = (
    {"id": "panhandle", "name": "Panhandle", "lat": 30.45, "lon": -86.05},
    {"id": "big_bend", "name": "Big Bend / Nature Coast", "lat": 29.35, "lon": -83.75},
    {"id": "northeast", "name": "Northeast Florida", "lat": 30.25, "lon": -81.45},
    {"id": "east_central", "name": "East Central (Space Coast)", "lat": 28.35, "lon": -80.75},
    {"id": "southeast", "name": "Southeast / Gold Coast", "lat": 26.15, "lon": -80.25},
    {"id": "southwest", "name": "Southwest Florida", "lat": 26.45, "lon": -81.85},
    {"id": "keys", "name": "Florida Keys", "lat": 24.65, "lon": -81.45},
)


class FloridaOceanTracker:
    """Track hurricanes and ocean storms threatening Florida"""

    def __init__(self):
        self.nhc_base = "https://www.nhc.noaa.gov"

    async def fetch_active_storms(self) -> List[Dict]:
        """Fetch active storms from NHC CurrentStorms.json (activeStorms)."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.nhc_base}/CurrentStorms.json",
                    timeout=10.0,
                )
                if response.status_code != 200:
                    return []
                data = response.json()
                raw = data.get("activeStorms") or data.get("active_storms") or []
                storms = []
                for storm in raw:
                    norm = self._normalize_storm_row(storm)
                    if norm:
                        storms.append(norm)
                return storms
            except Exception:
                return []

    def _normalize_storm_row(self, storm: Dict) -> Optional[Dict[str, Any]]:
        """Map varying NHC JSON keys to a single schema."""
        lat = storm.get("latitude") or storm.get("lat")
        lon = storm.get("longitude") or storm.get("lon")
        if lat is None or lon is None:
            loc = storm.get("location") or storm.get("currentPosition") or {}
            if isinstance(loc, dict):
                lat = lat or loc.get("latitude") or loc.get("lat")
                lon = lon or loc.get("longitude") or loc.get("lon")
        if lat is None or lon is None:
            return None
        ws = storm.get("windSpeed") or storm.get("wind_speed") or storm.get("maxWind")
        if ws is not None:
            ws = float(ws)
            if ws > 200:
                ws = ws / 1.94384
            elif ws <= 185:
                ws = ws * 1.15078
        direction = storm.get("direction") or storm.get("movementDir") or storm.get("movementDirection")
        if isinstance(direction, str):
            direction = self._compass_to_deg(direction) or 270.0
        spd = storm.get("movementSpeed") or storm.get("speed") or storm.get("forwardSpeed")
        return {
            "id": str(
                storm.get("id") or storm.get("stormId") or storm.get("name", "unknown")
            ),
            "name": storm.get("name") or storm.get("stormName") or "Unknown",
            "category": storm.get("category") or storm.get("classification"),
            "wind_speed": float(ws) if ws is not None else 0.0,
            "latitude": float(lat),
            "longitude": float(lon),
            "direction": float(direction) if direction is not None else 270.0,
            "speed": float(spd) if spd is not None else 12.0,
            "pressure": storm.get("pressure") or storm.get("minPressure"),
        }

    def _compass_to_deg(self, s: str) -> Optional[float]:
        m = {
            "N": 0,
            "NNE": 22.5,
            "NE": 45,
            "ENE": 67.5,
            "E": 90,
            "ESE": 112.5,
            "SE": 135,
            "SSE": 157.5,
            "S": 180,
            "SSW": 202.5,
            "SW": 225,
            "WSW": 247.5,
            "W": 270,
            "WNW": 292.5,
            "NW": 315,
            "NNW": 337.5,
        }
        return m.get(s.strip().upper())

    def _forward_speed_mph(self, storm: Dict) -> float:
        """NHC often reports forward motion in kt; convert to mph."""
        s = float(storm.get("speed") or 12.0)
        if s > 80:
            s = 15.0
        if s < 40:
            s = s * 1.15078
        return max(3.0, s)

    def _estimate_days_to_florida(self, storm: Dict) -> Optional[float]:
        """Rough ETA in days if moving toward Florida; None if likely outside 7-day window."""
        slat = float(storm.get("latitude") or 0)
        slon = float(storm.get("longitude") or 0)
        dist = self._distance_to_florida(slat, slon)
        speed_mph = self._forward_speed_mph(storm)
        hours = dist / max(speed_mph, 1.0)
        days = (hours / 24.0) * 1.12
        if not self._heading_toward_florida(slat, slon, float(storm.get("direction") or 270)):
            days *= 1.55
        return days

    def _region_risk_scores(self, storm: Dict, landfall_probability: float) -> List[Dict[str, Any]]:
        storm_lat = float(storm.get("latitude") or 0)
        storm_lon = float(storm.get("longitude") or 0)
        sdir = float(storm.get("direction") or 270)
        scores: List[Dict[str, Any]] = []
        for reg in FLORIDA_REGIONS:
            d_mi = self._haversine_distance(storm_lat, storm_lon, reg["lat"], reg["lon"])
            proximity = max(0.0, 1.0 - (d_mi / 950.0))
            bearing = self._bearing_deg(storm_lat, storm_lon, reg["lat"], reg["lon"])
            diff = abs(((bearing - sdir) + 180) % 360 - 180)
            align = max(0.38, 1.0 - diff / 200.0)
            risk = landfall_probability * proximity * align
            risk = min(95.0, max(0.0, risk))
            scores.append(
                {
                    "region_id": reg["id"],
                    "region": reg["name"],
                    "risk_percent": round(risk, 1),
                }
            )
        scores.sort(key=lambda x: x["risk_percent"], reverse=True)
        return scores

    @staticmethod
    def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        y = math.sin(math.radians(lon2 - lon1)) * math.cos(math.radians(lat2))
        x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(
            math.radians(lat1)
        ) * math.cos(math.radians(lat2)) * math.cos(math.radians(lon2 - lon1))
        return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0

    async def get_seven_day_outlook(self) -> Dict[str, Any]:
        """
        Storms that could threaten Florida within ~7 days: map positions, ETA day bucket,
        inland impact %, and regional risk breakdown.
        """
        storms_in = await self.fetch_active_storms()
        out_storms: List[Dict[str, Any]] = []
        for s in storms_in:
            slat = float(s.get("latitude") or 0)
            slon = float(s.get("longitude") or 0)
            dist_mi = self._distance_to_florida(slat, slon)
            eta = self._estimate_days_to_florida(s)
            if eta is None:
                continue
            if eta > 7.25 and dist_mi > 520:
                continue
            impact = self.calculate_florida_impact(s)
            lf = float(impact.get("landfall_probability") or 0)
            inland_pct = min(95.0, round(lf * 0.78 + min(12.0, lf * 0.08), 1))
            day_num = min(7, max(1, int(math.ceil(min(eta, 6.5)))))
            regions = self._region_risk_scores(s, lf)
            out_storms.append(
                {
                    "id": s.get("id"),
                    "name": s.get("name"),
                    "latitude": slat,
                    "longitude": slon,
                    "category": s.get("category"),
                    "wind_speed": s.get("wind_speed"),
                    "expected_day_inland": day_num,
                    "eta_days_model": round(eta, 2),
                    "inland_probability_percent": inland_pct,
                    "regions": regions[:7],
                }
            )
        return {
            "window_days": 7,
            "generated_at": datetime.now().isoformat(),
            "storm_count": len(out_storms),
            "storms": out_storms,
        }

    def calculate_florida_impact(self, storm: Dict) -> Dict:
        """Calculate probability and affected counties"""
        storm_lat = float(storm.get("latitude") or 0)
        storm_lon = float(storm.get("longitude") or 0)
        wind_speed = float(storm.get("wind_speed") or 0)
        direction = float(storm.get("direction") or 270)
        speed = float(storm.get("speed") or 0)

        distance = self._distance_to_florida(storm_lat, storm_lon)

        probability = self._calculate_probability(
            storm_lat, storm_lon, direction, speed, wind_speed, distance
        )

        affected = self._get_affected_counties(
            storm_lat, storm_lon, direction, probability
        )

        impact_zone = self._get_impact_zone(storm_lat, storm_lon, direction)

        return {
            "storm_name": storm.get("name"),
            "category": storm.get("category"),
            "wind_speed": wind_speed,
            "distance_to_florida_miles": round(distance, 1),
            "landfall_probability": probability,
            "impact_zone": impact_zone,
            "affected_counties": affected[:10],
            "recommendations": self._get_recommendations(
                probability, wind_speed, impact_zone
            ),
            "timestamp": datetime.now().isoformat(),
        }

    def _distance_to_florida(self, lat: float, lon: float) -> float:
        florida_lat, florida_lon = 27.8, -81.5
        return self._haversine_distance(lat, lon, florida_lat, florida_lon)

    def _haversine_distance(self, lat1, lon1, lat2, lon2) -> float:
        R = 3959
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(
            dlon / 2
        ) ** 2
        c = 2 * math.asin(math.sqrt(a))
        return R * c

    def _calculate_probability(self, lat, lon, direction, speed, wind_speed, distance) -> float:
        prob = 0

        if distance < 100:
            prob += 80
        elif distance < 300:
            prob += 50
        elif distance < 600:
            prob += 25
        else:
            prob += 10

        if self._heading_toward_florida(lat, lon, direction):
            prob += 30
        else:
            prob -= 20

        if wind_speed > 110:
            prob += 15
        elif wind_speed > 74:
            prob += 10

        return min(95, max(0, prob))

    def _heading_toward_florida(self, lat, lon, direction) -> bool:
        if lon > -80:
            return 270 <= direction <= 360
        if lon < -85:
            return 0 <= direction <= 180
        return True

    def _get_affected_counties(self, lat, lon, direction, probability) -> List[Dict]:
        affected = []
        centroids = florida_counties.get_county_centroids()

        for county_name, coords in centroids.items():
            clat = float(coords["lat"])
            clon = float(coords["lon"])
            distance = self._haversine_distance(lat, lon, clat, clon)
            risk = max(0, 100 - (distance / 10)) * (probability / 100)

            if risk > 10:
                affected.append(
                    {
                        "county": county_name,
                        "risk_percentage": round(min(95, risk), 1),
                        "evacuation_zone": evacuation_zone(county_name),
                    }
                )

        affected.sort(key=lambda x: x["risk_percentage"], reverse=True)
        return affected

    def _get_impact_zone(self, lat, lon, direction) -> str:
        if lon > -80:
            return "East Coast (Miami to Jacksonville)"
        if lon < -85:
            return "Gulf Coast (Tampa to Pensacola)"
        return "Keys & South Florida"

    def _get_recommendations(self, probability, wind_speed, impact_zone) -> List[str]:
        recs = []

        if probability > 70:
            recs.append(
                f"HIGH PROBABILITY - {impact_zone} prepare for landfall"
            )
            recs.append("Follow evacuation orders immediately")
        elif probability > 40:
            recs.append(f"MODERATE PROBABILITY - {impact_zone} monitor closely")
            recs.append("Complete emergency preparations")
        else:
            recs.append("LOW PROBABILITY - Continue monitoring")

        if wind_speed > 110:
            recs.append("MAJOR HURRICANE - Prepare for extended power outage")
        elif wind_speed > 74:
            recs.append("HURRICANE FORCE WINDS - Secure property")

        recs.append("Monitor: floridadisaster.org")
        return recs


florida_ocean = FloridaOceanTracker()
