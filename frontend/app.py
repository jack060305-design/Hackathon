"""
Florida Disaster Risk Prediction Platform
Main entry point for Streamlit app
"""

import streamlit as st
import requests
import os
from datetime import datetime

from pages import map as map_page
from pages import chatbot as chatbot_page

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Florida Disaster AI",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Global theme: animations, typography, cards (applies to all pages)
st.markdown(
    """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=Outfit:wght@500;600;700&display=swap" rel="stylesheet">
<style>
    html, body, [class*="css"]  {
        font-family: 'DM Sans', system-ui, sans-serif;
    }
    h1, h2, h3, .outfit {
        font-family: 'Outfit', 'DM Sans', sans-serif;
    }
    footer[data-testid="stFooter"] { visibility: hidden; height: 0; }

    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(18px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    @keyframes gradientFlow {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    @keyframes pulseGlow {
        0%, 100% { box-shadow: 0 0 0 0 rgba(56, 189, 248, 0.35); }
        50% { box-shadow: 0 0 24px 4px rgba(56, 189, 248, 0.2); }
    }
    .hero-wrap {
        position: relative;
        overflow: hidden;
        border-radius: 20px;
        padding: 2.5rem 2rem 2.25rem;
        margin-bottom: 2rem;
        background: linear-gradient(125deg, #0c1929 0%, #132f4c 35%, #0d3d5c 55%, #0a2840 100%);
        background-size: 200% 200%;
        animation: gradientFlow 14s ease infinite;
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 20px 50px rgba(0,0,0,0.35);
    }
    .hero-wrap::before {
        content: "";
        position: absolute;
        inset: 0;
        background: radial-gradient(ellipse 80% 60% at 20% 20%, rgba(56, 189, 248, 0.18), transparent 50%),
                    radial-gradient(ellipse 60% 50% at 85% 80%, rgba(34, 211, 238, 0.12), transparent 45%);
        pointer-events: none;
    }
    .hero-inner {
        position: relative;
        z-index: 1;
        text-align: center;
        color: #f0f9ff;
    }
    .hero-kicker {
        display: inline-block;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: #7dd3fc;
        margin-bottom: 0.75rem;
        animation: fadeInUp 0.7s ease both;
    }
    .hero-title {
        font-family: 'Outfit', sans-serif;
        font-size: clamp(1.85rem, 4vw, 2.65rem);
        font-weight: 700;
        line-height: 1.15;
        margin: 0 0 0.65rem;
        letter-spacing: -0.02em;
        animation: fadeInUp 0.75s ease 0.08s both;
    }
    .hero-sub {
        font-size: 1.05rem;
        color: rgba(224, 242, 254, 0.88);
        max-width: 36rem;
        margin: 0 auto 1.25rem;
        line-height: 1.5;
        animation: fadeInUp 0.8s ease 0.15s both;
    }
    .hero-badges {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        justify-content: center;
        animation: fadeInUp 0.85s ease 0.22s both;
    }
    .hero-badge {
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.12);
        padding: 0.35rem 0.85rem;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 500;
        color: #e0f2fe;
    }

    .section-title {
        font-family: 'Outfit', sans-serif;
        font-size: 1.35rem;
        font-weight: 600;
        color: #0c4a6e;
        margin: 0 0 1rem;
        letter-spacing: -0.02em;
    }
    .panel {
        background: linear-gradient(145deg, rgba(255,255,255,0.95), rgba(240, 249, 255, 0.92));
        border: 1px solid rgba(14, 116, 144, 0.12);
        border-radius: 16px;
        padding: 1.35rem 1.5rem;
        box-shadow: 0 8px 32px rgba(8, 47, 73, 0.08);
        animation: fadeInUp 0.6s ease both;
    }
    .panel-muted {
        color: #334155;
        font-size: 0.95rem;
        line-height: 1.6;
    }

    .feature-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    .feature-card {
        background: #fff;
        border: 1px solid rgba(14, 165, 233, 0.15);
        border-radius: 14px;
        padding: 1.15rem 1.2rem;
        transition: transform 0.25s ease, box-shadow 0.25s ease;
        animation: fadeInUp 0.55s ease both;
        box-shadow: 0 4px 20px rgba(8, 47, 73, 0.06);
    }
    .feature-card:nth-child(1) { animation-delay: 0.05s; }
    .feature-card:nth-child(2) { animation-delay: 0.1s; }
    .feature-card:nth-child(3) { animation-delay: 0.15s; }
    .feature-card:nth-child(4) { animation-delay: 0.2s; }
    .feature-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 36px rgba(8, 47, 73, 0.12);
    }
    .feature-icon { font-size: 1.6rem; margin-bottom: 0.5rem; display: block; }
    .feature-card h4 {
        font-family: 'Outfit', sans-serif;
        font-size: 0.95rem;
        font-weight: 600;
        color: #0c4a6e;
        margin: 0 0 0.35rem;
    }
    .feature-card p {
        margin: 0;
        font-size: 0.82rem;
        color: #64748b;
        line-height: 1.45;
    }

    .steps {
        counter-reset: step;
        list-style: none;
        padding: 0;
        margin: 0;
    }
    .steps li {
        position: relative;
        padding-left: 2.5rem;
        margin-bottom: 0.85rem;
        color: #334155;
        font-size: 0.92rem;
        line-height: 1.45;
    }
    .steps li::before {
        counter-increment: step;
        content: counter(step);
        position: absolute;
        left: 0;
        top: 0;
        width: 1.65rem;
        height: 1.65rem;
        background: linear-gradient(135deg, #0ea5e9, #0369a1);
        color: #fff;
        font-family: 'Outfit', sans-serif;
        font-size: 0.8rem;
        font-weight: 700;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 16px !important;
        border: 1px solid rgba(14, 165, 233, 0.18) !important;
        background: linear-gradient(165deg, rgba(255,255,255,0.98), rgba(240, 249, 255, 0.9)) !important;
        box-shadow: 0 8px 28px rgba(8, 47, 73, 0.07) !important;
        padding: 0.35rem 0.5rem 1rem !important;
        animation: fadeInUp 0.65s ease both;
    }

    .risk-high {
        background: linear-gradient(135deg, #ef4444, #b91c1c);
        padding: 1.1rem 1.25rem;
        border-radius: 14px;
        color: white;
        font-weight: 600;
        animation: fadeInUp 0.4s ease both;
        box-shadow: 0 8px 24px rgba(185, 28, 28, 0.35);
    }
    .risk-medium {
        background: linear-gradient(135deg, #f59e0b, #d97706);
        padding: 1.1rem 1.25rem;
        border-radius: 14px;
        color: #1c1917;
        font-weight: 600;
        animation: fadeInUp 0.4s ease both;
        box-shadow: 0 8px 24px rgba(217, 119, 6, 0.3);
    }
    .risk-low {
        background: linear-gradient(135deg, #22c55e, #15803d);
        padding: 1.1rem 1.25rem;
        border-radius: 14px;
        color: white;
        font-weight: 600;
        animation: fadeInUp 0.4s ease both;
        box-shadow: 0 8px 24px rgba(21, 128, 61, 0.3);
    }

    .emergency-bar {
        text-align: center;
        padding: 0.9rem 1rem;
        border-radius: 12px;
        background: linear-gradient(90deg, rgba(254, 226, 226, 0.9), rgba(254, 202, 202, 0.85));
        border: 1px solid rgba(220, 38, 38, 0.2);
        color: #7f1d1d;
        font-weight: 600;
        font-size: 0.9rem;
        animation: fadeIn 1s ease 0.3s both;
    }

    .status-pulse {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #22c55e;
        margin-right: 6px;
        animation: pulseGlow 2s ease-in-out infinite;
    }
    .status-pulse.off {
        background: #ef4444;
        animation: none;
    }

    .sidebar-section-title {
        font-family: 'Outfit', sans-serif;
        font-size: 0.95rem;
        font-weight: 600;
        color: #0c4a6e;
        margin-bottom: 0.5rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="hero-wrap">
  <div class="hero-inner">
    <div class="hero-kicker">Hackathon Demo · Florida Resilience</div>
    <h1 class="hero-title">🌊 Florida Disaster Risk Intelligence</h1>
    <p class="hero-sub">Machine Learning Estimates County Risk From Weather Signals—Clear, Fast, And Ready For Your Pitch.</p>
    <div class="hero-badges">
      <span class="hero-badge">Live API</span>
      <span class="hero-badge">Risk Map</span>
      <span class="hero-badge">Safety Assistant</span>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)


def show_home():
    st.markdown('<p class="section-title">Platform Overview</p>', unsafe_allow_html=True)

    col_main, col_side = st.columns([1.65, 1])

    with col_main:
        st.markdown(
            """
<div class="feature-grid">
  <div class="feature-card">
    <span class="feature-icon">🗺️</span>
    <h4>Real-Time Risk Map</h4>
    <p>County Markers And Severity At A Glance Across Florida.</p>
  </div>
  <div class="feature-card">
    <span class="feature-icon">🤖</span>
    <h4>ML Risk Scores</h4>
    <p>Wind, Rain, And Density Feed A Trained Risk Estimate.</p>
  </div>
  <div class="feature-card">
    <span class="feature-icon">💬</span>
    <h4>Preparedness Guide</h4>
    <p>Contextual Tips For Hurricanes, Floods, And Evacuation.</p>
  </div>
  <div class="feature-card">
    <span class="feature-icon">📡</span>
    <h4>Live Feeds</h4>
    <p>USGS, NOAA, And NWS Hooks Through Your Backend.</p>
  </div>
</div>
<div class="panel">
  <p class="section-title" style="margin-top:0;font-size:1.15rem;">How It Works</p>
  <ul class="steps">
    <li>Choose A Florida County And Current Conditions.</li>
    <li>Run A Prediction To Get A Normalized Risk Score.</li>
    <li>Read Actionable Recommendations By Risk Tier.</li>
    <li>Explore The Map And Assistant For Deeper Context.</li>
  </ul>
</div>
""",
            unsafe_allow_html=True,
        )

    with col_side:
        with st.container(border=True):
            st.markdown(
                '<p class="section-title" style="margin-top:0;font-size:1.1rem;">Quick Stats</p>',
                unsafe_allow_html=True,
            )
            try:
                response = requests.get(f"{API_URL}/api/prediction/counties", timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    clist = data.get("counties") or []
                    n = len(clist) if clist else 67
                else:
                    n = 67
            except Exception:
                n = "67"
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Counties Tracked", n)
            with c2:
                st.metric("Data Feeds", "4")
            st.metric("Evacuation Zones", "5", help="Illustrative Zones For Demo")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<p class="section-title">Quick Risk Assessment</p>', unsafe_allow_html=True
    )

    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            county = st.selectbox(
                "County",
                ["Miami-Dade", "Broward", "Palm Beach", "Hillsborough", "Orange", "Duval"],
            )
        with c2:
            wind = st.slider("Wind Speed (Mph)", 0, 150, 50)
        with c3:
            rain = st.slider("Rainfall (Inches)", 0.0, 20.0, 3.0)

        if st.button("Run Prediction", type="primary", use_container_width=True):
            with st.spinner("Analyzing Risk Factors…"):
                try:
                    response = requests.post(
                        f"{API_URL}/api/prediction/predict",
                        json={
                            "county": county,
                            "wind_speed": wind,
                            "rainfall": rain,
                            "population_density": "Medium",
                        },
                        timeout=5,
                    )
                    if response.status_code == 200:
                        result = response.json()
                        risk_score = result["risk_score"] * 100
                        if risk_score >= 70:
                            st.error(f"**High Risk** — {risk_score:.0f}%")
                            st.markdown(
                                '<div class="risk-high">Immediate Action Recommended</div>',
                                unsafe_allow_html=True,
                            )
                        elif risk_score >= 40:
                            st.warning(f"**Medium Risk** — {risk_score:.0f}%")
                            st.markdown(
                                '<div class="risk-medium">Prepare Supplies And Monitor Advisories</div>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.success(f"**Low Risk** — {risk_score:.0f}%")
                            st.markdown(
                                '<div class="risk-low">Stay Informed And Keep A Kit Ready</div>',
                                unsafe_allow_html=True,
                            )
                        st.markdown("**Recommendations**")
                        for rec in result["recommendations"]:
                            st.write(f"- {rec}")
                    else:
                        st.error("Unable To Reach Prediction Service")
                except Exception as e:
                    st.error(f"Connection Error: {e}")
                    st.info(
                        "Start The API: `python -m uvicorn app.main:app --reload --port 8000` From The Backend Folder."
                    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div class="emergency-bar">Emergency: Call 911 Immediately If You Are In Danger</div>',
        unsafe_allow_html=True,
    )


with st.sidebar:
    st.markdown(
        '<p class="sidebar-section-title">🧭 Navigation</p>', unsafe_allow_html=True
    )
    page = st.radio(
        "Select Page",
        ["🏠 Home", "🗺️ Risk Map", "💬 AI Assistant"],
        label_visibility="collapsed",
    )

    st.divider()

    st.markdown(
        '<p class="sidebar-section-title">🔌 System Status</p>', unsafe_allow_html=True
    )
    try:
        response = requests.get(f"{API_URL}/health", timeout=2)
        if response.status_code == 200:
            st.markdown(
                '<p><span class="status-pulse"></span><strong>Backend Connected</strong></p>',
                unsafe_allow_html=True,
            )
            st.caption(f"API Base: {API_URL}")
        else:
            st.markdown(
                '<p><span class="status-pulse off"></span><strong>Backend Issue</strong></p>',
                unsafe_allow_html=True,
            )
    except Exception:
        st.markdown(
            '<p><span class="status-pulse off"></span><strong>Backend Offline</strong></p>',
            unsafe_allow_html=True,
        )
        st.caption("Run Uvicorn On Localhost:8000")

    st.divider()

    st.markdown(
        '<p class="sidebar-section-title">📡 Data Sources</p>', unsafe_allow_html=True
    )
    st.markdown("- USGS Earthquakes")
    st.markdown("- NOAA Hurricanes")
    st.markdown("- NWS Weather")

    st.divider()

    st.markdown(
        '<p class="sidebar-section-title">⏰ Update Schedule</p>', unsafe_allow_html=True
    )
    st.markdown("**Every Seven Days** (Demo Cadence)")
    st.caption(f"Last Refresh Label: {datetime.now().strftime('%Y-%m-%d')}")

if page == "🏠 Home":
    show_home()
elif page == "🗺️ Risk Map":
    map_page.show()
elif page == "💬 AI Assistant":
    chatbot_page.show()
