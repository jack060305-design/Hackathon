"""
Florida disaster MCP server (stdio). County centroids + data catalog + **backend parity tools**
(same Python services as FastAPI in backend/app — inland map, ocean, USGS, risk model).

Run from repo root: python -m mcp_server.main

Streamlit uses HTTP on 127.0.0.1:8000; Cursor/IDE uses this MCP. Logic should stay aligned via shared
imports from backend/app (avoid duplicating fetch logic here).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

_REPO = Path(__file__).resolve().parent.parent
_CENTROIDS_PATH = _REPO / "data" / "florida_county_centroids.json"


def _ensure_backend_on_path() -> None:
    """Allow `from app.services...` — same package tree as uvicorn uses from backend/."""
    import sys

    backend_root = str((_REPO / "backend").resolve())
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)

# External data references (no secrets; clients fetch directly from these hosts)
NOAA_NOMADS_BASE = "https://nomads.ncep.noaa.gov/"
FLORIDA_DISASTER_SITE = "https://www.floridadisaster.org/"
# Public site may expose JSON under /api; confirm current paths on floridadisaster.org
FLORIDA_DISASTER_API_BASE = "https://www.floridadisaster.org/api"

_BUNDLED_DATA_RESOURCES: list[dict[str, str]] = [
    {
        "id": "county_centroids",
        "name": "Florida county centroids",
        "uri": "florida://counties/centroids.json",
        "description": (
            "Bundled 67 Florida counties with approximate centroid lat/lon for maps and tools."
        ),
    },
]

_EXTERNAL_DATA_SOURCES: list[dict[str, str]] = [
    {
        "id": "noaa_nomads",
        "name": "NOAA NOMADS",
        "title": "NOAA NCEP NOMADS",
        "base_url": NOAA_NOMADS_BASE,
        "description": (
            "Operational NCEP model output (e.g. GFS, NAM, HRRR) and GRIB filter services; "
            "use for forecast grids and time-series aligned with hurricane track planning."
        ),
    },
    {
        "id": "florida_disaster_api",
        "name": "Florida Disaster API",
        "title": "Florida Disaster (Division of Emergency Management)",
        "base_url": FLORIDA_DISASTER_SITE,
        "api_base": FLORIDA_DISASTER_API_BASE,
        "description": (
            "State emergency information; API routes change over time - "
            "use api_base as the starting point and follow official docs or network tab on the site."
        ),
    },
]


def _all_data_resources() -> list[dict[str, str]]:
    """Bundled file resources plus external NOAA / Florida Disaster endpoints (each with name)."""
    return [dict(r) for r in _BUNDLED_DATA_RESOURCES] + [
        dict(r) for r in _EXTERNAL_DATA_SOURCES
    ]

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


def _evacuation_zone(county: str) -> str:
    if county in ZONE_A:
        return "A"
    if county in ZONE_B:
        return "B"
    return "C"


def _load_centroids() -> dict[str, dict[str, float]]:
    if not _CENTROIDS_PATH.is_file():
        return {}
    return json.loads(_CENTROIDS_PATH.read_text(encoding="utf-8"))


mcp = FastMCP("Florida disaster county data")


@mcp.tool()
def list_florida_counties() -> list[str]:
    """Return all county names from bundled centroids (sorted)."""
    return sorted(_load_centroids().keys())


@mcp.tool()
def get_county_centroids() -> dict[str, dict[str, float]]:
    """County name -> {lat, lon} from data/florida_county_centroids.json."""
    return _load_centroids()


@mcp.tool()
def get_county_map_points() -> list[dict[str, Any]]:
    """All counties with lat, lon, and evacuation_zone (A / B / C)."""
    data = _load_centroids()
    out: list[dict[str, Any]] = []
    for name in sorted(data.keys()):
        c = data[name]
        out.append(
            {
                "name": name,
                "lat": c["lat"],
                "lon": c["lon"],
                "evacuation_zone": _evacuation_zone(name),
            }
        )
    return out


@mcp.resource("florida://counties/centroids.json")
def centroids_resource() -> str:
    """Raw JSON for county centroids (same file as on disk)."""
    if not _CENTROIDS_PATH.is_file():
        return "{}"
    return _CENTROIDS_PATH.read_text(encoding="utf-8")


@mcp.resource("florida://data-sources/noaa-nomads.json")
def resource_noaa_nomads_json() -> str:
    """NOAA NOMADS (nomads.ncep.noaa.gov); metadata for programmatic use."""
    return json.dumps(_EXTERNAL_DATA_SOURCES[0], indent=2) + "\n"


@mcp.resource("florida://data-sources/noaa-nomads.md")
def resource_noaa_nomads_md() -> str:
    """Human-readable notes for NOAA NCEP NOMADS."""
    meta = _EXTERNAL_DATA_SOURCES[0]
    return f"""# {meta["title"]}

- **Name:** {meta["name"]}
- **Base URL:** {NOAA_NOMADS_BASE}
- **Host:** `nomads.ncep.noaa.gov`
- **Role:** Distribution of NCEP operational model data (GRIB subsets, filters, and related guidance).
- **Usage:** Use HTTPS GET to the NOMADS UI or documented filter endpoints; respect NOAA [robots.txt](https://nomads.ncep.noaa.gov/robots.txt) and rate limits.

"""


@mcp.resource("florida://data-sources/floridadisaster-api.json")
def resource_florida_disaster_json() -> str:
    """Florida Disaster API base (floridadisaster.org/api); metadata."""
    return json.dumps(_EXTERNAL_DATA_SOURCES[1], indent=2) + "\n"


@mcp.resource("florida://data-sources/floridadisaster-api.md")
def resource_florida_disaster_md() -> str:
    """Human-readable notes for Florida Disaster public API entrypoint."""
    meta = _EXTERNAL_DATA_SOURCES[1]
    return f"""# {meta["title"]}

- **Name:** {meta["name"]}
- **Site:** {FLORIDA_DISASTER_SITE}
- **API base (typical):** {FLORIDA_DISASTER_API_BASE}
- **Role:** State of Florida emergency management public information; API surface may include alerts, maps, or content feeds.
- **Usage:** Discover current JSON routes from the live site or official documentation; do not assume undocumented paths remain stable.

"""


@mcp.resource("florida://data-sources/catalog.json")
def resource_data_sources_catalog() -> str:
    """All data resources (bundled URIs + external NOAA / Florida Disaster), each with name."""
    return json.dumps(_all_data_resources(), indent=2, ensure_ascii=False) + "\n"


@mcp.tool()
def get_external_data_sources() -> list[dict[str, str]]:
    """
    External NOAA NOMADS (nomads.ncep.noaa.gov) and Florida Disaster API bases
    (floridadisaster.org/api) for forecasts and state emergency data. Each entry includes name.
    """
    return [dict(item) for item in _EXTERNAL_DATA_SOURCES]


@mcp.tool()
def get_data_resources() -> list[dict[str, str]]:
    """Bundled MCP resources and external APIs; every item has id, name, and uri or base_url."""
    return _all_data_resources()


# ---------------------------------------------------------------------------
# Backend parity (shared with FastAPI — import backend/app services, do not reimplement)
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_inland_risk_map_json(limit: int = 40) -> dict[str, Any]:
    """Same JSON as GET /api/inland-risk-map — USGS + NWS inland markers (7-day)."""
    _ensure_backend_on_path()
    from app.services.inland_risk_map import fetch_inland_risk_markers

    return await fetch_inland_risk_markers(limit=limit)


@mcp.tool()
async def get_usgs_earthquakes_near_florida(limit: int = 10) -> list[dict[str, Any]]:
    """Same data as GET /api/disasters/usgs — earthquakes near Florida."""
    _ensure_backend_on_path()
    from app.services.usgs import fetch_earthquakes

    events = await fetch_earthquakes(limit=limit)
    return [e.model_dump() for e in events]


@mcp.tool()
async def get_ocean_seven_day_outlook() -> dict[str, Any]:
    """Same as GET /api/ocean/seven-day-outlook."""
    _ensure_backend_on_path()
    from app.services.florida_ocean_tracker import florida_ocean

    return await florida_ocean.get_seven_day_outlook()


@mcp.tool()
async def get_ocean_active_storms() -> dict[str, Any]:
    """Active storms (NHC) with count."""
    _ensure_backend_on_path()
    from app.services.florida_ocean_tracker import florida_ocean

    storms = await florida_ocean.fetch_active_storms()
    return {"count": len(storms), "storms": storms}


@mcp.tool()
async def get_ocean_coastal_risk_summary() -> dict[str, Any]:
    """Same logic as GET /api/ocean/coastal-risk."""
    _ensure_backend_on_path()
    from app.services.florida_ocean_tracker import florida_ocean

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
        max_prob = max(max_prob, float(impact["landfall_probability"]))
    if max_prob > 70:
        risk = "Extreme"
        advisory = "FLORIDA EMERGENCY - Prepare for landfall"
    elif max_prob > 40:
        risk = "High"
        advisory = "Monitor closely - Florida may be impacted"
    else:
        risk = "Moderate"
        advisory = "Watch conditions - Stay informed"
    return {
        "status": f"{len(storms)} active storm(s)",
        "coastal_risk": risk,
        "advisory": advisory,
        "storms": [{"name": s.get("name"), "category": s.get("category")} for s in storms],
    }


@mcp.tool()
def predict_disaster_risk_score(
    wind_speed: float,
    rainfall: float,
    population_density: str,
) -> dict[str, Any]:
    """Same model as POST /api/prediction/predict — risk_score in [0, 1]. population_density: Low|Medium|High."""
    _ensure_backend_on_path()
    from app.models import risk_model

    score = float(risk_model.predict(wind_speed, rainfall, population_density))
    level = "High" if score >= 0.7 else ("Medium" if score >= 0.4 else "Low")
    return {"risk_score": score, "risk_level": level}


@mcp.resource("florida://config/unified-stack.json")
def resource_unified_stack() -> str:
    """Single source of truth: HTTP routes vs MCP tools vs Python modules."""
    return json.dumps(
        {
            "codebase": "backend/app",
            "http_api_default_base": "http://127.0.0.1:8000",
            "streamlit_env": {"API_URL": "override base if API not on localhost:8000"},
            "inland_risk_map": {
                "http_get": [
                    "/api/inland-risk-map",
                    "/api/disasters/inland-risk-map",
                    "/api/disasters/inland_risk_map",
                ],
                "mcp_tool": "get_inland_risk_map_json",
                "python": "app.services.inland_risk_map.fetch_inland_risk_markers",
            },
            "usgs_earthquakes": {
                "http_get": "/api/disasters/usgs",
                "mcp_tool": "get_usgs_earthquakes_near_florida",
                "python": "app.services.usgs.fetch_earthquakes",
            },
            "ocean_outlook": {
                "http_get": "/api/ocean/seven-day-outlook",
                "mcp_tool": "get_ocean_seven_day_outlook",
                "python": "app.services.florida_ocean_tracker.florida_ocean",
            },
            "risk_model": {
                "http_post": "/api/prediction/predict",
                "mcp_tool": "predict_disaster_risk_score",
                "python": "app.models.risk_model",
            },
            "note": "MCP tools do not replace HTTP for Streamlit; they mirror the same services for Cursor IDE.",
        },
        indent=2,
        ensure_ascii=False,
    ) + "\n"


@mcp.resource("florida://architecture/http-vs-mcp.md")
def resource_http_vs_mcp() -> str:
    return """# HTTP API vs MCP (thống nhất / unified)

- **FastAPI** (`backend/`, `uvicorn app.main:app`, default **127.0.0.1:8000**): Streamlit gọi HTTP.
- **MCP** (stdio, Cursor): tools gọi **cùng module** `backend/app` — không nhân đôi logic USGS/NWS/ocean/ML.
- **Inland map** (USGS+NWS): NWS có **ngân sách thời gian** trên server để tránh treo. Streamlit: timeout đọc **180s** + **retry**. Fallback direct = **USGS+NWS** (parity với MCP/API). MCP **không** bind cổng HTTP — không xung đột với FastAPI.
- Xem **`florida://config/unified-stack.json`** để đối chiếu URL ↔ MCP tool ↔ hàm Python.

"""


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
