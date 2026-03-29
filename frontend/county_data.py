"""County names and map points from data/florida_county_centroids.json (no backend required)."""

import json
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
