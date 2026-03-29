"""
Inland disaster map points (non-hurricane): USGS earthquakes + NWS active alerts (inland types only).
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Any, List

import httpx

from .nws_alerts import collect_nws_inland_markers

_FL_LAT_MIN, _FL_LAT_MAX = 24.45, 31.05
_FL_LON_MIN, _FL_LON_MAX = -87.65, -79.85

_OFFSHORE_PAT = re.compile(
    r"offshore|atlantic ocean|gulf of mexico|barrier|nm\s+(?:ne|nw|se|sw|n|s|e|w)\s+of",
    re.I,
)


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


async def _collect_usgs_markers(
    client: httpx.AsyncClient, now: datetime, cap: int
) -> List[dict[str, Any]]:
    start = now - timedelta(days=7)
    # Smaller FDSN limit = faster response (still enough for FL inland filter)
    params = {
        "format": "geojson",
        "starttime": start.strftime("%Y-%m-%d"),
        "latitude": 27.8,
        "longitude": -81.5,
        "maxradiuskm": 650,
        "minmagnitude": 2.0,
        "orderby": "time",
        "limit": min(120, max(25, cap * 4)),
    }
    out: List[dict[str, Any]] = []

    response = await client.get(
        "https://earthquake.usgs.gov/fdsnws/event/1/query",
        params=params,
        timeout=httpx.Timeout(20.0),
    )
    if response.status_code != 200:
        return out
    data = response.json()

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
                "magnitude": float(mag) if mag is not None else None,
                "source": "usgs",
            }
        )
    return out


async def fetch_inland_risk_markers(limit: int = 60) -> dict[str, Any]:
    """
    Inland hazards only (no hurricanes): USGS earthquakes (7-day) + NWS active inland-type alerts.
    USGS and NWS run in parallel; one shared httpx client reuses connections.
    """
    now = datetime.now(timezone.utc)
    markers: List[dict[str, Any]] = []

    limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
    # NWS can use most of _NWS_PHASE_BUDGET_SEC; USGS is parallel — allow generous read timeout.
    timeout = httpx.Timeout(120.0, connect=10.0)
    async with httpx.AsyncClient(limits=limits, timeout=timeout, http2=False) as client:
        usgs_m, nws_m = await asyncio.gather(
            _collect_usgs_markers(client, now, limit),
            collect_nws_inland_markers(client, now, limit),
        )
    markers.extend(usgs_m)
    markers.extend(nws_m)

    markers.sort(key=lambda x: -float(x.get("risk_percent") or 0))
    return {
        "window_days": 7,
        "markers": markers[:limit],
        "sources": ["usgs_fdsnws", "nws_alerts"],
    }
