"""
Florida county helpers (Census / fallback). Optional use by other services.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import httpx

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_CENTROIDS_PATH = _REPO_ROOT / "data" / "florida_county_centroids.json"
_GEOJSON_PATH = _REPO_ROOT / "data" / "florida_counties.geojson"


def centroids_from_geojson(geojson_path: Path | None = None) -> Dict[str, Dict[str, float]]:
    """Parse point GeoJSON (name + lon/lat) into {county: {lat, lon}}."""
    path = geojson_path or _GEOJSON_PATH
    if not path.is_file():
        raise FileNotFoundError(f"Missing GeoJSON: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: Dict[str, Dict[str, float]] = {}
    for feat in raw.get("features") or []:
        props = feat.get("properties") or {}
        geom = feat.get("geometry") or {}
        name = props.get("name")
        coords = geom.get("coordinates")
        if not name or not coords or len(coords) < 2:
            continue
        lon, lat = float(coords[0]), float(coords[1])
        out[str(name)] = {"lat": lat, "lon": lon}
    return out

# Evacuation zones (simplified coastal tiers)
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

# All 67 Florida counties (alphabetical). Used when Census API fails or returns unexpected rows.
FLORIDA_COUNTIES_67: tuple[str, ...] = (
    "Alachua",
    "Baker",
    "Bay",
    "Bradford",
    "Brevard",
    "Broward",
    "Calhoun",
    "Charlotte",
    "Citrus",
    "Clay",
    "Collier",
    "Columbia",
    "DeSoto",
    "Dixie",
    "Duval",
    "Escambia",
    "Flagler",
    "Franklin",
    "Gadsden",
    "Gilchrist",
    "Glades",
    "Gulf",
    "Hamilton",
    "Hardee",
    "Hendry",
    "Hernando",
    "Highlands",
    "Hillsborough",
    "Holmes",
    "Indian River",
    "Jackson",
    "Jefferson",
    "Lafayette",
    "Lake",
    "Lee",
    "Leon",
    "Levy",
    "Liberty",
    "Madison",
    "Manatee",
    "Marion",
    "Martin",
    "Miami-Dade",
    "Monroe",
    "Nassau",
    "Okaloosa",
    "Okeechobee",
    "Orange",
    "Osceola",
    "Palm Beach",
    "Pasco",
    "Pinellas",
    "Polk",
    "Putnam",
    "Santa Rosa",
    "Sarasota",
    "Seminole",
    "St. Johns",
    "St. Lucie",
    "Sumter",
    "Suwannee",
    "Taylor",
    "Union",
    "Volusia",
    "Wakulla",
    "Walton",
    "Washington",
)

assert len(FLORIDA_COUNTIES_67) == 67


def _normalize_census_county_name(name: str) -> str:
    """Census NAME is like 'Alachua County, Florida' -> 'Alachua'."""
    if " County" in name:
        return name.split(" County", 1)[0].strip()
    return name.replace(", Florida", "").strip()


class FloridaCountyService:
    """Fetch Florida county names with Census fallback."""

    def __init__(self):
        self.cache: dict = {}
        self.census_api = "https://api.census.gov/data"
        self._centroids_cache: Dict[str, Dict[str, float]] | None = None

    def get_county_centroids(self) -> Dict[str, Dict[str, float]]:
        """Lat/lon approximations from county boundaries (see data/florida_county_centroids.json)."""
        if self._centroids_cache is not None:
            return self._centroids_cache
        if not _CENTROIDS_PATH.is_file():
            self._centroids_cache = {}
            return self._centroids_cache
        with open(_CENTROIDS_PATH, encoding="utf-8") as f:
            self._centroids_cache = json.load(f)
        return self._centroids_cache

    def get_county_map_points(self) -> List[Dict[str, Any]]:
        """All 67 counties with coordinates for mapping."""
        centroids = self.get_county_centroids()
        out: List[Dict[str, Any]] = []
        for name in FLORIDA_COUNTIES_67:
            c = centroids.get(name)
            if not c:
                continue
            out.append(
                {
                    "name": name,
                    "lat": c["lat"],
                    "lon": c["lon"],
                    "evacuation_zone": evacuation_zone(name),
                }
            )
        return out

    async def get_all_counties(self) -> List[str]:
        cache_key = "all_counties"
        if cache_key in self.cache:
            return self.cache[cache_key]

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.census_api}/2020/dec/pl",
                    params={
                        "get": "NAME",
                        "for": "county:*",
                        "in": "state:12",
                    },
                    timeout=10.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    rows = data[1:] if len(data) > 1 else []
                    counties = [_normalize_census_county_name(row[0]) for row in rows]
                    if len(counties) == 67:
                        self.cache[cache_key] = counties
                        return counties
            except Exception as e:
                print(f"Census API error: {e}")

        self.cache[cache_key] = list(FLORIDA_COUNTIES_67)
        return self.cache[cache_key]

    def export_centroids_json(self, output_path: Path | None = None) -> Path:
        """Write data/florida_county_centroids.json from florida_counties.geojson (frontend, MCP, scripts)."""
        return export_county_centroids_to_json(output_path)


florida_counties = FloridaCountyService()


def export_county_centroids_to_json(output_path: Path | None = None) -> Path:
    """
    Build data/florida_county_centroids.json from florida_counties.geojson.
    Counties follow FLORIDA_COUNTIES_67 order; overwrites output file.
    """
    path = output_path or _CENTROIDS_PATH
    by_name = centroids_from_geojson()
    ordered: Dict[str, Dict[str, float]] = {}
    missing: list[str] = []
    for name in FLORIDA_COUNTIES_67:
        c = by_name.get(name)
        if c:
            ordered[name] = c
        else:
            missing.append(name)
    if missing:
        raise ValueError(
            f"GeoJSON missing {len(missing)} counties (e.g. {missing[:5]} ...)"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(ordered, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    florida_counties._centroids_cache = None
    return path


if __name__ == "__main__":
    out = export_county_centroids_to_json()
    print(f"Wrote {out}")
