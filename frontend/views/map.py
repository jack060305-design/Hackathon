import json
import os
from pathlib import Path

import folium
import requests
import streamlit as st
from streamlit_folium import folium_static

from inland_direct_fetch import (
    fetch_inland_risk_markers_direct,
    fetch_usgs_feed_for_sidebar,
)


def _repo_root() -> Path:
    # frontend/views/map.py -> repo root
    return Path(__file__).resolve().parents[2]


def _fallback_inland_json() -> dict | None:
    p = _repo_root() / "data" / "inland_risk_fallback.json"
    if not p.is_file():
        return None
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) and "markers" in data else None
    except Exception:
        return None


def _api_bases() -> list[str]:
    env = os.getenv("API_URL", "").strip()
    if env:
        return [env.rstrip("/")]
    # Single default — avoid :8001 unless you run a second API there (was causing confusing 404 in errors)
    return ["http://127.0.0.1:8000"]


def _wrong_app_hint(base: str) -> str | None:
    """If /health works but OpenAPI has no inland map paths, another app may own this port."""
    try:
        h = requests.get(f"{base}/health", timeout=3)
        if h.status_code != 200:
            return None
        o = requests.get(f"{base}/openapi.json", timeout=6)
        if o.status_code != 200:
            return None
        paths = (o.json() or {}).get("paths") or {}
        for p in paths:
            pl = p.lower()
            if "inland" in pl or "inland-risk" in pl or "inland_risk" in pl:
                return None
        return (
            f"**{base}** responds to `/health`, but **`/openapi.json` has no inland map routes** — "
            "this is probably **not** the Hackathon API. Close other servers on port **8000**, open a terminal in **`backend/`**, run: "
            "`python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`."
        )
    except Exception:
        return None


# Try short alias first (registered on app in main.py), then router paths.
_INLAND_PATHS = (
    "/api/inland-risk-map",
    "/api/disasters/inland-risk-map",
    "/api/disasters/inland_risk_map",
)

# Server: USGS + NWS (NWS có ngân sách ~52s) — cần đọc dài hơn /health; retry 1 lần khi timeout
_INLAND_HTTP_TIMEOUT = (10, 180)


def _api_health_ok(base: str) -> bool:
    try:
        r = requests.get(f"{base}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def _conn_retryable(err: str) -> bool:
    m = err.lower()
    return "timeout" in m or "timed out" in m or "read timed out" in m


def _fetch_inland_risk_map():
    """Returns (data dict with markers, base url) or (None, error_meta)."""
    last_err = None
    for base in _api_bases():
        for path in _INLAND_PATHS:
            url = f"{base}{path}"
            for attempt in range(2):
                try:
                    r = requests.get(url, timeout=_INLAND_HTTP_TIMEOUT)
                    if r.status_code == 200:
                        data = r.json()
                        if isinstance(data, dict) and "markers" in data:
                            return data, base
                    last_err = ("http", r.status_code, url, r.text[:500])
                    break
                except Exception as e:
                    err_s = str(e)
                    last_err = ("conn", err_s, url, "")
                    if attempt == 0 and _conn_retryable(err_s):
                        continue
                    break
    return None, last_err


def _default_api_base() -> str:
    return os.getenv("API_URL", "http://127.0.0.1:8000").strip().rstrip("/") or "http://127.0.0.1:8000"


def _direct_mode_help_markdown() -> str:
    base = _default_api_base()
    return f"""
**Tiếng Việt**
- Fallback gọi thẳng **USGS + NWS** — **cùng nguồn** với API và MCP (`fetch_inland_risk_markers`). MCP **không** chiếm cổng 8000; nếu inland lỗi, thường do **timeout** hoặc **process khác** trên cổng 8000.
- Chạy API từ **`backend/`**:
  ```text
  python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
  ```
- **`API_URL`** mặc định `{base}`.

**English**
- Direct fallback = **USGS + NWS** only (parity with API/MCP). MCP uses the same Python module; it does not conflict with HTTP.

**HTTP / MCP**
- `GET /api/inland-risk-map` → `fetch_inland_risk_markers`
- MCP `get_inland_risk_map_json` → same function
"""


def _api_connection_hint(api_err_meta: tuple | None, backend_alive: bool) -> str:
    """One-line diagnosis when inland HTTP failed but direct feeds worked."""
    if not api_err_meta:
        return ""
    kind = api_err_meta[0]
    if kind == "conn":
        msg = str(api_err_meta[1]).lower()
        if backend_alive and ("timeout" in msg or "timed out" in msg):
            return (
                "Inland **timeout** dù **`/health` OK** — đã tăng đọc **180s** và **retry 1 lần**. "
                "Backend NWS có giới hạn thời gian; nếu vẫn lỗi, kiểm tra đúng app Hackathon trên cổng 8000."
            )
        return "Lỗi kết nối — kiểm tra API và **`API_URL`**."
    if kind == "http":
        code = api_err_meta[1]
        if code == 404:
            return "HTTP 404 — có thể **sai app** trên cổng (không phải Hackathon API). Khởi động `uvicorn` từ **`backend/`**."
        return f"HTTP {code} — xem chi tiết bên dưới."
    return ""


def _risk_color(risk_pct: float) -> tuple[str, str]:
    if risk_pct >= 70:
        return "red", "darkred"
    if risk_pct >= 40:
        return "orange", "orangered"
    return "green", "lightgreen"


def show():
    st.subheader("Inland Disaster Risk Map")
    st.markdown(
        "**Non-hurricane** inland hazards: **USGS** earthquakes (7-day) and **NWS** active alerts "
        "(flood, severe thunderstorm, tornado, fire weather, wind, winter, heat, etc.). "
        "Each point: **% risk**, **type**, **next N days**, **source**."
    )

    data, meta = _fetch_inland_risk_map()
    api_err_meta = None
    if data is None:
        api_err_meta = meta
        # Same agencies as backend/MCP: USGS + NWS (see inland_direct_fetch)
        direct = fetch_inland_risk_markers_direct(limit=60)
        if direct is not None:
            data = direct
            meta = "direct_feeds (USGS+NWS, parity with API/MCP)"
            base = _default_api_base()
            alive = _api_health_ok(base)
            if alive:
                st.info(
                    f"**`/api/inland-risk-map`** không phản hồi kịp hoặc lỗi — đang dùng **USGS + NWS** trực tiếp "
                    f"(cùng dữ liệu với **`fetch_inland_risk_markers`** / MCP). **MCP không xung đột** với API. "
                    f"Kiểm tra đúng **Hackathon API** trên `{base}`.",
                    icon="📡",
                )
            else:
                st.info(
                    f"**API** `{base}` không khả dụng. Đang dùng **USGS + NWS** trực tiếp (giống backend/MCP).",
                    icon="📡",
                )
            diag = _api_connection_hint(api_err_meta, alive)
            if diag:
                st.caption(diag)
            with st.expander("Cách sửa / Fix: bật API thống nhất · MCP · `API_URL`", expanded=False):
                st.markdown(_direct_mode_help_markdown())
            if st.button("Thử lại kết nối API / Retry API", key="retry_inland_api"):
                st.rerun()
        else:
            hint = None
            for b in _api_bases():
                hint = _wrong_app_hint(b)
                if hint:
                    break
            fb = _fallback_inland_json()
            if fb is not None:
                n_demo = len(fb.get("markers") or [])
                st.warning(
                    "Could not reach the API **or** public feeds (network/offline). Showing **demo markers** "
                    f"({n_demo} points). Check internet and **`backend/`** on **127.0.0.1:8000**."
                )
                if hint:
                    with st.expander("Why is the API failing?", expanded=False):
                        st.markdown(hint)
                if api_err_meta:
                    with st.expander("Technical detail (last API attempt)", expanded=False):
                        if api_err_meta[0] == "http":
                            _, code, url, body = api_err_meta
                            st.caption(f"`{url}` → HTTP **{code}**")
                            if body:
                                st.code(body[:800], language="text")
                        else:
                            _, err, url, _ = api_err_meta
                            st.caption(f"`{url}`")
                            st.code(err, language="text")
                data = fb
                meta = "demo_fallback.json (offline)"
            else:
                st.error("Could not load inland risk data from the API or public feeds.")
                if hint:
                    st.markdown(hint)
                if api_err_meta and api_err_meta[0] == "http":
                    _, code, url, body = api_err_meta
                    st.caption(f"`{url}` → HTTP **{code}**")
                    if body:
                        st.code(body[:800], language="text")
                st.info(
                    "Run **`run-project.ps1`** or from **`backend/`**: "
                    "`python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`."
                )
                return

    srcs = ", ".join(data.get("sources") or [])
    mstr = str(meta)
    if not mstr.startswith("direct") and "demo_fallback" not in mstr.lower():
        st.caption(f"**API:** `{mstr}` — live data từ backend · **Sources:** `{srcs}`")
    else:
        st.caption(f"**Chế độ / Mode:** `{meta}` · **Sources:** `{srcs}`")

    markers = data.get("markers") or []
    m = folium.Map(
        location=[27.8, -81.5],
        zoom_start=6,
        tiles="OpenStreetMap",
    )

    if not markers:
        st.info(
            "No **inland** hazard points in this response "
            "(no signals in the last window, filtered offshore, or empty API result)."
        )
    else:
        for mk in markers:
            lat = float(mk["lat"])
            lon = float(mk["lon"])
            risk = float(mk.get("risk_percent") or 0)
            dtype = mk.get("disaster_type") or "unknown"
            next_days = int(mk.get("next_days") or 1)
            label = mk.get("label") or dtype
            detail = mk.get("detail") or ""
            src = mk.get("source") or ""

            color, fill_color = _risk_color(risk)
            radius = max(6, min(22, risk / 4.5))

            popup_html = (
                f"<b>{label}</b><br>"
                f"Type: {dtype}<br>"
                f"Risk: <b>{risk:.1f}%</b><br>"
                f"Next {next_days} day(s) in outlook<br>"
                f"Source: {src}<br>"
                f"<small>{detail}</small>"
            )
            folium.CircleMarker(
                location=[lat, lon],
                radius=radius,
                popup=folium.Popup(popup_html, max_width=300),
                color=color,
                fill=True,
                fillColor=fill_color,
                fillOpacity=0.6,
                weight=2,
                tooltip=f"{dtype} · {risk:.0f}% · next {next_days}d · {src}",
            ).add_to(m)

    legend_html = """
    <div style="position: fixed; bottom: 96px; left: 50px; z-index: 9999;
                background: white; padding: 12px; border-radius: 8px;
                border: 2px solid #ccc; box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                font-family: Arial; font-size: 14px;">
    <b>Inland risk (non-hurricane)</b><br>
    <span style="color:red">●</span> High (70%+)<br>
    <span style="color:orange">●</span> Medium (40–70%)<br>
    <span style="color:green">●</span> Lower (&lt;40%)<br>
    <hr style="margin: 5px 0;">
    <span>USGS · NWS (API / MCP / direct)</span>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    folium_static(m, width=900, height=600)

    st.divider()
    st.subheader("Live feed (inland / USGS)")
    with st.expander("Recent earthquake feed (same region, detail)"):
        try:
            events = None
            for base in _api_bases():
                try:
                    r = requests.get(f"{base}/api/disasters/usgs?limit=8", timeout=8)
                    if r.status_code == 200:
                        events = r.json()
                        break
                except Exception:
                    continue
            if not events:
                events = fetch_usgs_feed_for_sidebar(limit=8)
                if events:
                    st.caption("*(USGS via direct feed — API unavailable)*")
            if events:
                for eq in events:
                    mag = eq.get("magnitude", "N/A")
                    loc = eq.get("location", "Unknown")
                    st.write(f"• **M {mag}** — {loc}")
            else:
                st.write("Unable to fetch USGS list.")
        except Exception as e:
            st.write(f"Error: {e}")
