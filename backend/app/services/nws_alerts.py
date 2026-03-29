"""
Weather.gov (NWS) API — active alerts for Florida, used by inland risk map and health check.
https://www.weather.gov/documentation/services-web-api

Minimal ``requests`` pattern (sync; same shape as our httpx calls below)::

    import requests
    headers = {
        "User-Agent": "(FloridaDisasterHackathon) inland-risk-map/1.0 (contact: local-dev)",
        "Accept": "application/geo+json",
    }
    endpoint = f"{NWS_API_BASE}/alerts/active"
    response = requests.get(endpoint, params={"area": "FL"}, headers=headers, timeout=25)
    data = response.json()
    print(data.get("features", []))

Tutorials often show ``GET /alerts?area=ST``. We use **/alerts/active** so we only get
*currently active* alerts (appropriate for a live risk map). ``/alerts`` can return a
broader set depending on query filters.
"""

from __future__ import annotations

import asyncio
import re
import time
from datetime import datetime, timezone
from typing import Any

import httpx

# Hard cap so GET /api/inland-risk-map stays within reverse-proxy / Streamlit timeouts (~90–180s
# total with USGS in parallel). Without this, many zone lookups can run for minutes.
_NWS_PHASE_BUDGET_SEC = 52.0
_NWS_MAX_FEATURES_CAP = 28
_NWS_ZONE_TIMEOUT_SEC = 8.0
_NWS_MAX_ZONES_PER_ALERT = 3

NWS_API_BASE = "https://api.weather.gov"
# Live hazards only — see module docstring.
NWS_ALERTS_ACTIVE_PATH = "/alerts/active"
NWS_DEFAULT_AREA = "FL"

# api.weather.gov requires a descriptive User-Agent (plain "myapp" may be rate-limited or rejected).
NWS_DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": "(FloridaDisasterHackathon) inland-risk-map/1.0 (contact: local-dev)",
    "Accept": "application/geo+json",
}

_FL_LAT_MIN, _FL_LAT_MAX = 24.45, 31.05
_FL_LON_MIN, _FL_LON_MAX = -87.65, -79.85

_NWS_SKIP_EVENTS = re.compile(
    r"tropical|hurricane|typhoon|storm surge|marine|beach hazards|rip current|"
    r"small craft|gale|tsunami|coastal flood|high surf|waterspout|special marine|heavy surf",
    re.I,
)


def _in_florida_bbox(lat: float, lon: float) -> bool:
    return _FL_LAT_MIN <= lat <= _FL_LAT_MAX and _FL_LON_MIN <= lon <= _FL_LON_MAX


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

    sev_adj = {"Extreme": 1.12, "Severe": 1.06, "Moderate": 1.0, "Minor": 0.88}.get(
        sev, 1.0
    )
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


async def fetch_active_alerts_fl_geojson(
    client: httpx.AsyncClient,
) -> dict[str, Any] | None:
    """GET ``{NWS_API_BASE}{NWS_ALERTS_ACTIVE_PATH}?area=FL`` — parsed JSON or None on failure."""
    endpoint = f"{NWS_API_BASE}{NWS_ALERTS_ACTIVE_PATH}"
    try:
        r = await client.get(
            endpoint,
            params={"area": NWS_DEFAULT_AREA},
            headers=NWS_DEFAULT_HEADERS,
            timeout=httpx.Timeout(25.0),
        )
    except Exception:
        return None
    if r.status_code != 200:
        return None
    try:
        return r.json()
    except Exception:
        return None


async def _nws_zone_point(
    client: httpx.AsyncClient, cache: dict[str, tuple[float, float]], zone_url: str
) -> tuple[float, float] | None:
    if zone_url in cache:
        return cache[zone_url]
    try:
        r = await client.get(
            zone_url, headers=NWS_DEFAULT_HEADERS, timeout=_NWS_ZONE_TIMEOUT_SEC
        )
        if r.status_code != 200:
            return None
        zj = r.json()
        pt = _geometry_to_point(zj.get("geometry"))
        if pt:
            cache[zone_url] = pt
        return pt
    except Exception:
        return None


async def collect_nws_inland_markers(
    client: httpx.AsyncClient, now: datetime, cap: int
) -> list[dict[str, Any]]:
    """
    Inland-relevant NWS alerts for FL: geometry or affectedZones centroid, bbox filter, skip marine/tropical.
    Stops early when `_NWS_PHASE_BUDGET_SEC` is exceeded so the HTTP handler finishes reliably.
    """
    out: list[dict[str, Any]] = []
    zone_cache: dict[str, tuple[float, float]] = {}
    deadline = time.monotonic() + _NWS_PHASE_BUDGET_SEC

    data = await fetch_active_alerts_fl_geojson(client)
    if not data:
        return out

    max_features = min(_NWS_MAX_FEATURES_CAP, max(18, min(cap * 2, 40)))
    for feature in data.get("features", [])[:max_features]:
        if time.monotonic() > deadline:
            break
        props = feature.get("properties", {})
        event = props.get("event") or ""
        if not event or _NWS_SKIP_EVENTS.search(event):
            continue

        pt = _geometry_to_point(feature.get("geometry"))
        if not pt:
            zones = (props.get("affectedZones") or [])[:_NWS_MAX_ZONES_PER_ALERT]
            if zones:
                pts = await asyncio.gather(
                    *(_nws_zone_point(client, zone_cache, zu) for zu in zones),
                    return_exceptions=True,
                )
                for p in pts:
                    if isinstance(p, Exception):
                        continue
                    if p:
                        pt = p
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


async def nws_active_alerts_health() -> dict[str, Any]:
    """Same entrypoint as inland map — for diagnostics."""
    url = f"{NWS_API_BASE}{NWS_ALERTS_ACTIVE_PATH}"
    try:
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        timeout = httpx.Timeout(20.0, connect=5.0)
        async with httpx.AsyncClient(limits=limits, timeout=timeout, http2=False) as client:
            r = await client.get(
                url,
                params={"area": NWS_DEFAULT_AREA},
                headers=NWS_DEFAULT_HEADERS,
                timeout=20.0,
            )
        n = 0
        if r.status_code == 200:
            data = r.json()
            n = len(data.get("features") or [])
        return {
            "ok": r.status_code == 200,
            "status_code": r.status_code,
            "feature_count": n,
            "url": url,
            "note": "NWS is also used inside GET /api/inland-risk-map (not shown as its own data product in older builds).",
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "url": url,
        }
