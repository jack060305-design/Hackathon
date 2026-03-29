"""
When the FastAPI backend is unreachable or inland HTTP fails, build the same inland map
payload by calling public feeds directly (requests). **Default matches** ``backend``
``fetch_inland_risk_markers``: **USGS + NWS only** (same sources as API and MCP
``get_inland_risk_map_json``). Optional NASA EONET is off by default to avoid drift from MCP.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

_FL_LAT_MIN, _FL_LAT_MAX = 24.45, 31.05
_FL_LON_MIN, _FL_LON_MAX = -87.65, -79.85

_OFFSHORE_PAT = re.compile(
    r"offshore|atlantic ocean|gulf of mexico|barrier|nm\s+(?:ne|nw|se|sw|n|s|e|w)\s+of",
    re.I,
)

_NWS_SKIP_EVENTS = re.compile(
    r"tropical|hurricane|typhoon|storm surge|marine|beach hazards|rip current|"
    r"small craft|gale|tsunami|coastal flood|high surf|waterspout|special marine|heavy surf",
    re.I,
)

# Match backend app.services.nws_alerts.NWS_DEFAULT_HEADERS (User-Agent required by api.weather.gov).
_NWS_HEADERS = {
    "User-Agent": "(FloridaDisasterHackathon) inland-risk-map/1.0 (contact: local-dev)",
    "Accept": "application/geo+json",
}


def _in_florida_bbox(lat: float, lon: float) -> bool:
    return _FL_LAT_MIN <= lat <= _FL_LAT_MAX and _FL_LON_MIN <= lon <= _FL_LON_MAX


def _is_inland_event(place: str, lat: float, lon: float) -> bool:
    if not place:
        return True
    if _OFFSHORE_PAT.search(place):
        return False
    if lon > -79.2 and lat > 26.0:
        return False
    return True


def _risk_percent_eq(magnitude: float | None, days_since: int) -> float:
    mag = float(magnitude) if magnitude is not None else 2.5
    base = min(92.0, 6.0 + mag * 15.0)
    recency = max(0.35, 1.0 - (days_since / 7.5))
    return round(min(95.0, base * recency), 1)


def _next_days_eq(days_since: int) -> int:
    return max(1, min(7, 7 - days_since))


def _ring_centroid(ring: list) -> tuple[float, float] | None:
    if not ring or len(ring) < 3:
        return None
    lons = [float(p[0]) for p in ring]
    lats = [float(p[1]) for p in ring]
    return sum(lats) / len(lats), sum(lons) / len(lons)


def _geometry_to_point(geom: dict | None) -> tuple[float, float] | None:
    if not geom or not isinstance(geom, dict):
        return None
    gtype = geom.get("type")
    coords = geom.get("coordinates")
    if gtype == "Point" and coords and len(coords) >= 2:
        return float(coords[1]), float(coords[0])
    if gtype == "Polygon" and coords and coords[0]:
        c = _ring_centroid(coords[0])
        return c if c else None
    if gtype == "MultiPolygon" and coords and coords[0] and coords[0][0]:
        c = _ring_centroid(coords[0][0])
        return c if c else None
    return None


def _nws_risk_and_type(event_name: str, severity: str | None) -> tuple[float, str]:
    en = (event_name or "weather").lower()
    sev = (severity or "Moderate").strip()

    if "tornado" in en:
        slug, base = "tornado", 86.0
    elif "flash flood" in en or "flood" in en:
        slug, base = "flood", 68.0
    elif "severe thunderstorm" in en:
        slug, base = "severe_thunderstorm", 58.0
    elif "extreme wind" in en or "high wind" in en or "wind advisory" in en:
        slug, base = "wind", 52.0
    elif "fire" in en or "red flag" in en:
        slug, base = "fire_weather", 55.0
    elif "winter" in en or "freeze" in en or "ice" in en:
        slug, base = "winter", 48.0
    elif "heat" in en:
        slug, base = "heat", 52.0
    elif "dense fog" in en:
        slug, base = "fog", 35.0
    else:
        slug, base = "weather", 45.0

    sev_adj = {"Extreme": 1.12, "Severe": 1.06, "Moderate": 1.0, "Minor": 0.88}.get(sev, 1.0)
    risk = min(94.0, base * sev_adj)
    return round(risk, 1), slug


def _parse_iso_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _nws_zone_point(
    session: requests.Session, cache: dict[str, tuple[float, float]], zone_url: str
) -> tuple[float, float] | None:
    if zone_url in cache:
        return cache[zone_url]
    try:
        r = session.get(zone_url, headers=_NWS_HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        zj = r.json()
        pt = _geometry_to_point(zj.get("geometry"))
        if pt:
            cache[zone_url] = pt
        return pt
    except Exception:
        return None


def _collect_usgs_markers(now: datetime, cap: int) -> list[dict[str, Any]]:
    start = now - timedelta(days=7)
    params = {
        "format": "geojson",
        "starttime": start.strftime("%Y-%m-%d"),
        "latitude": 27.8,
        "longitude": -81.5,
        "maxradiuskm": 650,
        "minmagnitude": 2.0,
        "orderby": "time",
        "limit": min(200, max(30, cap * 5)),
    }
    out: list[dict[str, Any]] = []
    try:
        response = requests.get(
            "https://earthquake.usgs.gov/fdsnws/event/1/query",
            params=params,
            timeout=15,
        )
        if response.status_code != 200:
            return out
        data = response.json()
    except Exception:
        return out

    for feature in data.get("features", []):
        props = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        coords = geometry.get("coordinates", [0, 0, 0])
        lon, lat = float(coords[0]), float(coords[1])
        place = props.get("place") or ""

        if not _in_florida_bbox(lat, lon):
            continue
        if not _is_inland_event(place, lat, lon):
            continue

        t_ms = props.get("time")
        if t_ms is None:
            continue
        try:
            ev = datetime.fromtimestamp(t_ms / 1000.0, tz=timezone.utc)
        except (OSError, ValueError, TypeError):
            continue

        days_since = (now - ev).days
        if days_since >= 7:
            continue

        mag = props.get("mag")
        risk = _risk_percent_eq(mag, days_since)
        next_d = _next_days_eq(days_since)
        if risk < 5.0:
            continue

        out.append(
            {
                "lat": lat,
                "lon": lon,
                "risk_percent": risk,
                "disaster_type": "earthquake",
                "next_days": next_d,
                "label": f"M {mag}" if mag is not None else "Earthquake",
                "detail": place[:200],
                "source": "usgs",
            }
        )
    return out


def _collect_nws_markers(now: datetime, cap: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    zone_cache: dict[str, tuple[float, float]] = {}
    session = requests.Session()

    try:
        response = session.get(
            "https://api.weather.gov/alerts/active",
            params={"area": "FL"},
            headers=_NWS_HEADERS,
            timeout=20,
        )
        if response.status_code != 200:
            return out
        data = response.json()
    except Exception:
        return out

    max_features = min(60, max(35, cap * 2))
    for feature in data.get("features", [])[:max_features]:
        props = feature.get("properties", {})
        event = props.get("event") or ""
        if not event or _NWS_SKIP_EVENTS.search(event):
            continue

        pt = _geometry_to_point(feature.get("geometry"))
        if not pt:
            for zu in props.get("affectedZones") or []:
                pt = _nws_zone_point(session, zone_cache, zu)
                if pt:
                    break
        if not pt:
            continue

        lat, lon = pt
        if not _in_florida_bbox(lat, lon):
            continue

        severity = props.get("severity")
        risk, slug = _nws_risk_and_type(event, severity)

        exp = _parse_iso_dt(props.get("expires"))
        if exp:
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            delta = exp - now.astimezone(timezone.utc)
            hours = max(0.0, delta.total_seconds() / 3600.0)
            next_d = max(1, min(7, int(max(1.0, hours / 24.0 + 0.99))))
        else:
            next_d = 2

        headline = (props.get("headline") or event)[:200]
        desc = props.get("description") or ""
        detail = headline if len(headline) > 20 else (desc[:200] if desc else headline)

        out.append(
            {
                "lat": lat,
                "lon": lon,
                "risk_percent": risk,
                "disaster_type": slug,
                "next_days": next_d,
                "label": event[:80],
                "detail": detail,
                "source": "nws",
            }
        )
    return out


_EONET_SKIP = re.compile(r"hurricane|tropical|cyclone|marine|water|tsunami", re.I)


def _collect_eonet_markers(now: datetime, cap: int) -> list[dict[str, Any]]:
    """NASA EONET open events — points in Florida bbox (wildfire, storm, flood categories)."""
    out: list[dict[str, Any]] = []
    try:
        r = requests.get(
            "https://eonet.gsfc.nasa.gov/api/v3/events/status/open",
            params={"days": 7, "limit": 120},
            timeout=22,
        )
        if r.status_code != 200:
            return out
        payload = r.json()
    except Exception:
        return out

    events = payload.get("events") or []
    for ev in events:
        title = (ev.get("title") or "")[:120]
        if _EONET_SKIP.search(title):
            continue
        cats = ev.get("categories") or []
        cat_id = ""
        if cats:
            cat_id = (cats[0].get("id") or "").lower()
        if "severe" not in cat_id and "wildfire" not in cat_id and "floods" not in cat_id and "storms" not in cat_id:
            if not any(x in title.lower() for x in ("fire", "flood", "storm", "severe")):
                continue

        geoms = ev.get("geometry") or ev.get("geometries") or []
        for g in geoms[:5]:
            coords = g.get("coordinates")
            if not coords or len(coords) < 2:
                continue
            lon = float(coords[0])
            lat = float(coords[1])
            try:
                lat_f = float(lat)
                lon_f = float(lon)
            except (TypeError, ValueError):
                continue
            if g.get("type") and str(g.get("type")).lower() not in ("point",):
                continue
            if not _in_florida_bbox(lat_f, lon_f):
                continue
            risk = 42.0
            if "wildfire" in cat_id or "fire" in title.lower():
                risk = 58.0
            elif "flood" in cat_id or "flood" in title.lower():
                risk = 52.0
            elif "storm" in cat_id or "severe" in cat_id:
                risk = 48.0
            out.append(
                {
                    "lat": lat_f,
                    "lon": lon_f,
                    "risk_percent": risk,
                    "disaster_type": "eonet_" + (cat_id.split("_")[-1] if cat_id else "event"),
                    "next_days": 3,
                    "label": title[:80] or "EONET event",
                    "detail": (ev.get("description") or "")[:200],
                    "source": "eonet",
                }
            )
            break
        if len(out) >= max(8, cap // 3):
            break
    return out


# Same labels as backend inland JSON when EONET is disabled.
SOURCE_LINEAGE_BACKEND: list[str] = ["usgs_fdsnws", "nws_alerts"]

# Optional extended lineage if ``include_eonet=True``.
SOURCE_LINEAGE_WITH_EONET: list[str] = [
    "usgs_fdsnws",
    "nws_alerts",
    "nasa_eonet",
    "noaa_via_weather_gov",
    "multi_agency_regional",
]


def fetch_inland_risk_markers_direct(
    limit: int = 60, *, include_eonet: bool = False
) -> dict[str, Any] | None:
    """
    Same shape as backend inland JSON. Default **USGS + NWS only** — parity with API/MCP.
    Returns None only if both core pulls fail hard.
    """
    now = datetime.now(timezone.utc)
    markers: list[dict[str, Any]] = []

    try:
        markers.extend(_collect_usgs_markers(now, limit))
        markers.extend(_collect_nws_markers(now, limit))
        if include_eonet:
            markers.extend(_collect_eonet_markers(now, limit))
    except Exception:
        pass

    if not markers:
        return None

    markers.sort(key=lambda x: -float(x.get("risk_percent") or 0))
    sources = (
        SOURCE_LINEAGE_WITH_EONET.copy() if include_eonet else SOURCE_LINEAGE_BACKEND.copy()
    )
    note = (
        "Streamlit direct: USGS + NWS + EONET (EONET optional)."
        if include_eonet
        else "Streamlit direct: USGS + NWS — same agencies as fetch_inland_risk_markers / MCP."
    )
    return {
        "window_days": 7,
        "markers": markers[:limit],
        "sources": sources,
        "_direct": True,
        "_note": note,
    }


def fetch_usgs_feed_for_sidebar(limit: int = 8) -> list[dict[str, Any]] | None:
    """Recent earthquakes for expander when backend /api/disasters/usgs is down."""
    try:
        r = requests.get(
            "https://earthquake.usgs.gov/fdsnws/event/1/query",
            params={
                "format": "geojson",
                "starttime": (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d"),
                "latitude": 27.8,
                "longitude": -81.5,
                "maxradiuskm": 650,
                "minmagnitude": 2.0,
                "orderby": "time",
                "limit": limit,
            },
            timeout=12,
        )
        if r.status_code != 200:
            return None
        feats = r.json().get("features") or []
        out = []
        for f in feats:
            p = f.get("properties") or {}
            out.append(
                {
                    "magnitude": p.get("mag"),
                    "location": p.get("place") or "Unknown",
                }
            )
        return out
    except Exception:
        return None
