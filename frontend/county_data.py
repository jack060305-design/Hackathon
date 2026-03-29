"""County names and map points from data/florida_county_centroids.json (no backend required)."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

_HERE = Path(__file__).resolve()
_NAME = "florida_county_centroids.json"


def _centroids_path() -> Path | None:
    """Resolve JSON: env, repo data/, frontend/data/, or cwd-relative (Streamlit cwd is often frontend/)."""
    env = os.getenv("FLORIDA_CENTROIDS_JSON", "").strip()
    if env:
        p = Path(env).expanduser()
        if p.is_file():
            return p
    candidates = [
        _HERE.parent.parent / "data" / _NAME,
        _HERE.parent / "data" / _NAME,
        Path.cwd() / "data" / _NAME,
        Path.cwd().parent / "data" / _NAME,
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None

# Same coastal tiers as backend/app/services/florida_counties.py
ZONE_A: frozenset[str] = frozenset(
    {
        "Miami-Dade",
        "Broward",
        "Monroe",
        "Collier",
        "Lee",
        "Charlotte",
        "Sarasota",
        "Manatee",
        "Pinellas",
        "Bay",
        "Escambia",
        "Okaloosa",
        "Santa Rosa",
        "Walton",
        "Gulf",
        "Franklin",
        "Taylor",
    }
)
ZONE_B: frozenset[str] = frozenset(
    {
        "Palm Beach",
        "Martin",
        "St. Lucie",
        "Indian River",
        "Brevard",
        "Volusia",
        "Flagler",
        "St. Johns",
        "Duval",
        "Nassau",
        "Citrus",
        "Hernando",
        "Levy",
        "Wakulla",
    }
)


def evacuation_zone(county: str) -> str:
    if county in ZONE_A:
        return "A"
    if county in ZONE_B:
        return "B"
    return "C"


def county_names_fallback() -> list:
    p = _centroids_path()
    if p is None:
        return ["Miami-Dade", "Broward", "Orange", "Duval"]
    data = json.loads(p.read_text(encoding="utf-8"))
    return sorted(data.keys())


def get_county_map_points_offline() -> list[dict]:
    """Same shape as GET /api/prediction/county-map: name, lat, lon, evacuation_zone."""
    p = _centroids_path()
    if p is None:
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    out: list[dict] = []
    for name in sorted(data.keys()):
        c = data[name]
        out.append(
            {
                "name": name,
                "lat": c["lat"],
                "lon": c["lon"],
                "evacuation_zone": evacuation_zone(name),
            }
        )
    return out


def fetch_county_names(api_base: str | None = None) -> list:
    """Bundled centroids JSON only; api_base is ignored (kept for call sites)."""
    return county_names_fallback()


# Rough Florida bounding box (inland risk map / UI)
_FL_LAT_MIN, _FL_LAT_MAX = 24.45, 31.05
_FL_LON_MIN, _FL_LON_MAX = -87.65, -79.85


def is_in_florida_bbox(lat: float, lon: float) -> bool:
    return _FL_LAT_MIN <= lat <= _FL_LAT_MAX and _FL_LON_MIN <= lon <= _FL_LON_MAX


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p = math.pi / 180.0
    a = 0.5 - math.cos((lat2 - lat1) * p) / 2.0 + math.cos(lat1 * p) * math.cos(
        lat2 * p
    ) * (1.0 - math.cos((lon2 - lon1) * p)) / 2.0
    return 2.0 * r * math.asin(min(1.0, math.sqrt(a)))


def nearest_county_from_latlon(lat: float, lon: float) -> tuple[str | None, float]:
    """Return (county name, distance km) from bundled centroids, or (None, inf) if no data."""
    p = _centroids_path()
    if p is None:
        return None, float("inf")
    data = json.loads(p.read_text(encoding="utf-8"))
    best_name: str | None = None
    best_km = float("inf")
    for name, c in data.items():
        clat, clon = float(c["lat"]), float(c["lon"])
        d = _haversine_km(lat, lon, clat, clon)
        if d < best_km:
            best_km = d
            best_name = name
    return best_name, best_km
