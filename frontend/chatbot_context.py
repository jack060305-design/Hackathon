"""
Fetch inland risk + ocean outlook for the AI Assistant status announcement.
"""

from __future__ import annotations

import os
from typing import Any

import requests

from county_data import is_in_florida_bbox, nearest_county_from_latlon

_INLAND_TIMEOUT = (8, 90)
_OCEAN_TIMEOUT = (5, 20)


def api_bases() -> list[str]:
    env = os.getenv("API_URL", "").strip()
    if env:
        return [env.rstrip("/")]
    return [
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8001",
        "http://localhost:8000",
    ]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import math

    r = 6371.0
    p = math.pi / 180.0
    a = 0.5 - math.cos((lat2 - lat1) * p) / 2.0 + math.cos(lat1 * p) * math.cos(
        lat2 * p
    ) * (1.0 - math.cos((lon2 - lon1) * p)) / 2.0
    return 2.0 * r * math.asin(min(1.0, math.sqrt(a)))


def fetch_inland_markers_near(api_base: str, lat: float, lon: float, limit: int = 60) -> list[dict[str, Any]]:
    paths = (
        "/api/inland-risk-map",
        "/api/disasters/inland-risk-map",
    )
    for path in paths:
        url = f"{api_base}{path}"
        try:
            r = requests.get(url, params={"limit": limit}, timeout=_INLAND_TIMEOUT)
            if r.status_code != 200:
                continue
            data = r.json()
            if isinstance(data, dict) and isinstance(data.get("markers"), list):
                return data["markers"]
        except Exception:
            continue
    return []


def nearest_inland_highlights(
    markers: list[dict[str, Any]], lat: float, lon: float, max_points: int = 4, radius_km: float = 280.0
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


def fetch_ocean_outlook(api_base: str) -> dict[str, Any] | None:
    url = f"{api_base}/api/ocean/seven-day-outlook"
    try:
        r = requests.get(url, timeout=_OCEAN_TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            return data if isinstance(data, dict) else None
    except Exception:
        pass
    return None


def fetch_coastal_risk(api_base: str) -> dict[str, Any] | None:
    url = f"{api_base}/api/ocean/coastal-risk"
    try:
        r = requests.get(url, timeout=_OCEAN_TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            return data if isinstance(data, dict) else None
    except Exception:
        pass
    return None


def pick_working_api_base() -> tuple[str | None, str | None]:
    """Return (base_url, error_message)."""
    last_err = None
    for base in api_bases():
        try:
            r = requests.get(f"{base}/health", timeout=4)
            if r.status_code == 200:
                return base, None
        except Exception as e:
            last_err = str(e)
    return None, last_err or "Could not reach API"


def build_status_markdown(
    *,
    lat: float,
    lon: float,
    county: str | None,
    in_florida: bool,
    inland_near: list[dict[str, Any]],
    ocean: dict[str, Any] | None,
    coastal: dict[str, Any] | None,
) -> str:
    lines: list[str] = []
    lines.append("### Your status check")
    lines.append(
        f"**Coordinates:** `{lat:.4f}, {lon:.4f}`  \n"
        f"**Nearest Florida county (centroid):** {county or '—'}  \n"
    )
    if not in_florida:
        lines.append(
            "*Note: coordinates look **outside** the usual Florida map box; inland highlights may be sparse.*\n"
        )

    lines.append("#### Inland risk (Risk Map feed)")
    if not inland_near:
        lines.append(
            "- No ranked hazard markers within ~280 km, or API unavailable. Open **Risk Map** for full state data."
        )
    else:
        for m in inland_near:
            label = str(m.get("label") or m.get("disaster_type") or "Hazard")[:80]
            risk = m.get("risk_percent")
            src = m.get("source", "")
            nd = m.get("next_days", "")
            try:
                rp = float(risk) if risk is not None else None
            except (TypeError, ValueError):
                rp = None
            rs = f"{rp:.0f}%" if rp is not None else "—"
            lines.append(
                f"- **{label}** — risk **{rs}** · next ~**{nd}** day(s) · source `{src}`"
            )

    lines.append("#### Ocean tracking")
    if coastal:
        lines.append(
            f"- **Coastal outlook:** {coastal.get('coastal_risk', '—')} — _{coastal.get('advisory', '')}_"
        )
        st = coastal.get("status")
        if st:
            lines.append(f"- **Status:** {st}")
    if ocean:
        sc = ocean.get("storm_count")
        if sc is not None:
            lines.append(f"- **Storms in 7-day window (modeled):** {sc}")
        storms = ocean.get("storms") or []
        if isinstance(storms, list) and storms:
            for s in storms[:4]:
                if isinstance(s, dict):
                    nm = s.get("name") or s.get("id") or "Storm"
                    cat = s.get("category", "")
                    eta = s.get("eta_days_model")
                    inn = s.get("inland_probability_percent")
                    eta_s = f"{float(eta):.1f}" if eta is not None else "—"
                    inn_s = f"{float(inn):.0f}" if inn is not None else "—"
                    lines.append(
                        f"- **{nm}** — ETA ~**{eta_s}** d · inland % ~**{inn_s}** · cat `{cat}`"
                    )
        elif sc == 0:
            lines.append("- No tropical systems modeled toward Florida in the next ~7 days (per backend outlook).")
        elif not coastal:
            lines.append("- Outlook response had no storm list (check API).")
    elif not coastal:
        lines.append("- Ocean outlook unavailable (API offline or timeout).")

    return "\n".join(lines)


def load_context_for_location(lat: float, lon: float) -> tuple[str, str | None, str | None]:
    """
    Returns (markdown announcement, working_api_base or None, nearest_county or None).
    """
    base, err = pick_working_api_base()
    if base is None:
        return (
            "### Location received\n"
            f"Could not reach the backend API ({err}). "
            "Start the API from `backend/` and try **Check location / status** again.",
            None,
            None,
        )

    in_fl = is_in_florida_bbox(lat, lon)
    county, _km = nearest_county_from_latlon(lat, lon)

    markers = fetch_inland_markers_near(base, lat, lon)
    near = nearest_inland_highlights(markers, lat, lon)
    ocean = fetch_ocean_outlook(base)
    coastal = fetch_coastal_risk(base)

    md = build_status_markdown(
        lat=lat,
        lon=lon,
        county=county,
        in_florida=in_fl,
        inland_near=near,
        ocean=ocean,
        coastal=coastal,
    )
    return md, base, county
