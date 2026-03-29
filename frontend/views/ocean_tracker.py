"""
Florida Ocean Tracker: 7-day hurricane outlook map + inland % and regional risk.
"""

import os

import folium
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import folium_static


def _api_bases() -> list[str]:
    """If API_URL is unset, try common ports (8000 then 8001) — avoids 'No outlook data' when backend uses another port."""
    env = os.getenv("API_URL", "").strip()
    if env:
        return [env.rstrip("/")]
    return [
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8001",
        "http://localhost:8000",
    ]


def _fetch_seven_day_outlook():
    """Returns (outlook_dict, base_url_used) or (None, last_error_tuple)."""
    last_err: tuple | None = None
    for base in _api_bases():
        url = f"{base}/api/ocean/seven-day-outlook"
        try:
            r = requests.get(url, timeout=12)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict):
                    return data, base
            last_err = ("http", r.status_code, url, r.text[:600])
        except Exception as e:
            last_err = ("conn", str(e), url, "")
    return None, last_err

_DAY_COLORS = [
    "#d73027",
    "#fc8d59",
    "#fee08b",
    "#d9ef8b",
    "#91cf60",
    "#1a9850",
    "#006837",
]


def _marker_color(day: int) -> str:
    return _DAY_COLORS[min(6, max(0, day - 1))]


def show():
    st.subheader("7-Day Hurricane Outlook (Florida)")
    st.caption(
        "Map shows tropical cyclones modeled to reach Florida within ~7 days. "
        "Inland % and regional risks are heuristic estimates from NHC position and motion."
    )

    outlook, meta = _fetch_seven_day_outlook()
    if outlook is None:
        st.error("Could not load the 7-day outlook from the backend.")
        if meta:
            kind = meta[0]
            if kind == "http":
                _, code, url, body = meta
                st.caption(f"Request: `{url}` → HTTP **{code}**")
                if body:
                    st.code(body, language="text")
            else:
                _, err, url, _ = meta
                st.caption(f"Request: `{url}`")
                st.code(err, language="text")
        st.info(
            "Start the API from the `backend` folder, e.g. "
            "`python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` "
            "(or port **8001** if 8000 is busy). "
            "Optional: set env **API_URL** to the exact base URL."
        )
        return

    st.caption(f"Connected to API: **{meta}**")

    storms = outlook.get("storms") or []
    m = folium.Map(location=[24.8, -81.5], zoom_start=6, tiles="CartoDB positron")

    folium.Rectangle(
        bounds=[[24.0, -87.8], [31.2, -79.8]],
        color="#2c7fb8",
        weight=1,
        fill=True,
        fill_opacity=0.04,
        popup="Florida area",
    ).add_to(m)

    if not storms:
        st.info(
            "No tropical cyclones in the **7-day Florida window** right now "
            "(NHC may report no active storms, or all systems are outside the modeled window)."
        )
    else:
        for storm in storms:
            lat = float(storm.get("latitude") or 0)
            lon = float(storm.get("longitude") or 0)
            day = int(storm.get("expected_day_inland") or 1)
            name = storm.get("name") or "Unknown"
            inland = storm.get("inland_probability_percent")
            pop_html = (
                f"<b>{name}</b><br>"
                f"ETA day (modeled): {day}<br>"
                f"Inland impact (est.): {inland}%<br>"
                f"Wind (est. mph): {storm.get('wind_speed', 'n/a')}"
            )
            folium.CircleMarker(
                location=[lat, lon],
                radius=10 + min(8, day),
                popup=folium.Popup(pop_html, max_width=280),
                color=_marker_color(day),
                fill=True,
                fillColor=_marker_color(day),
                fillOpacity=0.85,
                weight=2,
                tooltip=f"{name} · day {day} · inland ~{inland}%",
            ).add_to(m)

    legend_html = """
    <div style="position: fixed; bottom: 48px; left: 48px; z-index: 1000;
            background: white; padding: 10px 12px; border-radius: 8px;
            border: 1px solid #ccc; font-size: 13px; max-width: 260px;">
    <b>Marker color</b> ≈ earlier (red) → later (green) modeled inland day (1–7).<br>
    <span style="font-size:11px;color:#555;">Data: NHC CurrentStorms + backend heuristics</span>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    folium_static(m, width=900, height=520)

    st.divider()
    st.subheader("Outlook detail")

    if storms:
        rows = []
        for storm in storms:
            rows.append(
                {
                    "Storm": storm.get("name"),
                    "Day (est. inland)": storm.get("expected_day_inland"),
                    "ETA (days, model)": storm.get("eta_days_model"),
                    "Inland % (est.)": storm.get("inland_probability_percent"),
                    "Wind (mph est.)": round(float(storm.get("wind_speed") or 0), 1),
                    "Lat": storm.get("latitude"),
                    "Lon": storm.get("longitude"),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown("**Regions possibly affected (risk %, heuristic)**")
        for storm in storms:
            nm = storm.get("name") or "Storm"
            with st.expander(f"{nm} - inland ~{storm.get('inland_probability_percent')}%"):
                regs = storm.get("regions") or []
                if regs:
                    st.dataframe(
                        pd.DataFrame(regs)[["region", "risk_percent"]].rename(
                            columns={"region": "Region", "risk_percent": "Risk %"}
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.caption("No regional breakdown.")
    else:
        st.caption("No rows while the 7-day list is empty.")

    with st.expander("About this model"):
        st.markdown(
            """
- **7-day filter:** Uses distance to Florida, forward speed, and heading vs. modeled ETA; drops systems beyond ~7.25 days unless already near the state.
- **Inland %:** Scaled from landfall-style probability (not an official NHC product).
- **Regions:** Seven Florida sub-regions; risk blends distance, track alignment, and overall threat score.
- **Source:** [NHC CurrentStorms.json](https://www.nhc.noaa.gov/CurrentStorms.json) via backend.
            """
        )
