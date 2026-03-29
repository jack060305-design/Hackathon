import streamlit as st
import folium
from streamlit_folium import folium_static
import requests
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")


def show():
    st.markdown(
        '<p class="section-title">Florida County Risk Map</p>', unsafe_allow_html=True
    )
    st.caption(
        "Interactive Markers For Sample County Risk Levels—Circle Size Reflects Relative Severity."
    )

    m = folium.Map(
        location=[27.8, -81.5],
        zoom_start=7,
        tiles="CartoDB positron",
    )

    risk_data = {
        "Miami-Dade": {"risk": 0.82, "coords": [25.76, -80.19]},
        "Broward": {"risk": 0.75, "coords": [26.12, -80.14]},
        "Palm Beach": {"risk": 0.68, "coords": [26.64, -80.13]},
        "Hillsborough": {"risk": 0.52, "coords": [27.95, -82.46]},
        "Orange": {"risk": 0.38, "coords": [28.54, -81.38]},
        "Duval": {"risk": 0.35, "coords": [30.33, -81.65]},
        "Pinellas": {"risk": 0.55, "coords": [27.96, -82.73]},
        "Polk": {"risk": 0.32, "coords": [27.95, -81.70]},
        "Lee": {"risk": 0.45, "coords": [26.64, -81.87]},
        "Brevard": {"risk": 0.42, "coords": [28.29, -80.72]},
    }

    for county, info in risk_data.items():
        risk = info["risk"]
        if risk >= 0.7:
            color = "red"
            fill_color = "darkred"
        elif risk >= 0.4:
            color = "orange"
            fill_color = "orange"
        else:
            color = "green"
            fill_color = "green"

        folium.CircleMarker(
            location=info["coords"],
            radius=risk * 25,
            popup=f"""
            <b>{county}</b><br>
            Risk: {risk*100:.0f}%<br>
            <span style="color:{color}">●</span> {color.upper()} Alert
            """,
            color=color,
            fill=True,
            fillColor=fill_color,
            fillOpacity=0.6,
            tooltip=f"{county}: {risk*100:.0f}% Risk",
        ).add_to(m)

    legend_html = """
    <div style="position: fixed; bottom: 50px; left: 50px; z-index: 1000;
                background: rgba(255,255,255,0.95); padding: 14px 16px; border-radius: 12px;
                border: 1px solid rgba(14, 116, 144, 0.2); box-shadow: 0 8px 24px rgba(0,0,0,0.12);
                font-family: 'DM Sans', system-ui, sans-serif; font-size: 13px; backdrop-filter: blur(8px);">
    <b style="font-size:14px;">Risk Level Key</b><br>
    <span style="color:#dc2626">●</span> High (70–100%)<br>
    <span style="color:#ea580c">●</span> Medium (40–70%)<br>
    <span style="color:#16a34a">●</span> Low (0–40%)<br>
    <hr style="margin: 8px 0; border: none; border-top: 1px solid #e2e8f0;">
    <span style="color:#64748b;">Circle Size ∝ Severity</span>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    folium_static(m, width=1000, height=520)

    st.divider()
    st.markdown(
        '<p class="section-title" style="font-size:1.15rem;">Live Feeds From Backend</p>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        with st.expander("USGS Earthquake Data", expanded=False):
            try:
                response = requests.get(f"{API_URL}/api/disasters/usgs?limit=3", timeout=5)
                if response.status_code == 200:
                    events = response.json()
                    if events:
                        for eq in events:
                            mag = eq.get("magnitude", "N/A")
                            location = eq.get("location", "Unknown")
                            st.write(f"• **Magnitude {mag}** — {location}")
                    else:
                        st.write("No Recent Earthquakes")
                else:
                    st.write("Unable To Fetch USGS Data")
            except Exception as e:
                st.write(f"Connection Error: {e}")

    with col2:
        with st.expander("NOAA Hurricane Data", expanded=False):
            try:
                response = requests.get(
                    f"{API_URL}/api/disasters/noaa/hurricanes", timeout=5
                )
                if response.status_code == 200:
                    storms = response.json()
                    for storm in storms:
                        name = storm.get("name", "Unknown")
                        category = storm.get("category", "N/A")
                        st.write(f"• **{name}** — Category {category}")
                else:
                    st.write("No Active Hurricanes")
            except Exception as e:
                st.write(f"Connection Error: {e}")
