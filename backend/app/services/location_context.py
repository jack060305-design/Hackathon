"""
Aggregate inland + ocean data for a point (lat, lon).

The browser obtains coordinates via the W3C Geolocation API (navigator.geolocation);
this module runs the same fusion used by the Streamlit AI Assistant (no HTTP self-calls).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .florida_ocean_tracker import florida_ocean
from .inland_risk_map import fetch_inland_risk_markers

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_CENTROIDS_PATH = _REPO_ROOT / "data" / "florida_county_centroids.json"

_FL_LAT_MIN, _FL_LAT_MAX = 24.45, 31.05
_FL_LON_MIN, _FL_LON_MAX = -87.65, -79.85


def _in_florida_bbox(lat: float, lon: float) -> bool:
    return _FL_LAT_MIN <= lat <= _FL_LAT_MAX and _FL_LON_MIN <= lon <= _FL_LON_MAX


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p = math.pi / 180.0
    a = 0.5 - math.cos((lat2 - lat1) * p) / 2.0 + math.cos(lat1 * p) * math.cos(
        lat2 * p
    ) * (1.0 - math.cos((lon2 - lon1) * p)) / 2.0
    return 2.0 * r * math.asin(min(1.0, math.sqrt(a)))


def _load_centroids() -> dict[str, dict[str, float]]:
    if not _CENTROIDS_PATH.is_file():
        return {}
    data = json.loads(_CENTROIDS_PATH.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def nearest_county(lat: float, lon: float) -> tuple[str | None, float]:
    data = _load_centroids()
    best: str | None = None
    best_km = float("inf")
    for name, c in data.items():
        try:
            clat = float(c["lat"])
            clon = float(c["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        d = _haversine_km(lat, lon, clat, clon)
        if d < best_km:
            best_km = d
            best = str(name)
    return best, best_km


def nearest_inland_highlights(
    markers: list[dict[str, Any]],
    lat: float,
    lon: float,
    max_points: int = 4,
    radius_km: float = 280.0,
) -> list[dict[str, Any]]:
    scored: list[tuple[float, dict[str, Any]]] = []
    for m in markers:
        try:
            ml = float(m.get("lat"))
            mo = float(m.get("lon"))
        except (TypeError, ValueError):
            continue
        d = _haversine_km(lat, lon, ml, mo)
        if d <= radius_km:
            scored.append((d, m))
    scored.sort(key=lambda x: x[0])
    return [m for _, m in scored[:max_points]]


async def _coastal_risk_summary() -> dict[str, Any]:
    storms = await florida_ocean.fetch_active_storms()
    if not storms:
        return {
            "status": "No active storms",
            "coastal_risk": "Low",
            "advisory": "No tropical cyclones threatening Florida",
        }
    max_prob = 0.0
    for storm in storms:
        impact = florida_ocean.calculate_florida_impact(storm)
        max_prob = max(max_prob, float(impact.get("landfall_probability") or 0))
    if max_prob > 70:
        risk, advisory = "Extreme", "FLORIDA EMERGENCY - Prepare for landfall"
    elif max_prob > 40:
        risk, advisory = "High", "Monitor closely - Florida may be impacted"
    else:
        risk, advisory = "Moderate", "Watch conditions - Stay informed"
    return {
        "status": f"{len(storms)} active storm(s)",
        "coastal_risk": risk,
        "advisory": advisory,
        "storms": [{"name": s.get("name"), "category": s.get("category")} for s in storms],
    }


async def build_location_context(
    lat: float, lon: float, inland_limit: int = 80
) -> dict[str, Any]:
    """
    Returns JSON suitable for OpenAPI and for clients after Geolocation API success.
    """
    county, dist_km = nearest_county(lat, lon)
    inland_payload = await fetch_inland_risk_markers(limit=inland_limit)
    markers = inland_payload.get("markers") or []
    highlights = nearest_inland_highlights(markers, lat, lon)
    ocean = await florida_ocean.get_seven_day_outlook()
    coastal = await _coastal_risk_summary()

    return {
        "note": (
            "Coordinates are normally obtained in the browser via the W3C Geolocation API "
            "(navigator.geolocation.getCurrentPosition). This endpoint does not call Geolocation itself."
        ),
        "lat": lat,
        "lon": lon,
        "in_florida_bbox": _in_florida_bbox(lat, lon),
        "nearest_county": county,
        "nearest_county_distance_km": round(dist_km, 2) if math.isfinite(dist_km) else None,
        "inland_highlights_nearby": highlights,
        "ocean_seven_day_outlook": ocean,
        "coastal_risk": coastal,
        "sources": inland_payload.get("sources"),
    }
