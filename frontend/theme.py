"""
Shared visual theme: palette, typography (Plus Jakarta Sans), Streamlit overrides.
Blue + near-black surfaces, electric blue accents.
"""

from __future__ import annotations

# —— Blue / black night theme ——
COLORS = {
    "primary": "#3b82f6",
    "primary_dark": "#1d4ed8",
    "primary_light": "#60a5fa",
    "primary_soft": "rgba(59, 130, 246, 0.12)",
    "accent": "#38bdf8",
    "accent_light": "#7dd3fc",
    "sand": "#0f1419",
    "bg": "#050608",
    "surface": "#0c1017",
    "surface_elevated": "#131a24",
    "text": "#f1f5f9",
    "text_muted": "#94a3b8",
    "success": "#34d399",
    "warning": "#fbbf24",
    "danger": "#f87171",
    "border": "#1e293b",
    "border_strong": "#334155",
    "sidebar_1": "#06080c",
    "sidebar_2": "#0a1628",
    "header_grad_1": "#020617",
    "header_grad_2": "#0f172a",
    "header_border": "#1e40af92",
}


def theme_css() -> str:
    c = COLORS
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0&display=swap');

html, body, .stApp, [data-testid="stMarkdownContainer"] p, .stMarkdown {{
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
}}

.material-symbols-outlined {{
    font-family: 'Material Symbols Outlined';
    font-weight: normal;
    font-style: normal;
    font-size: 1.35em;
    line-height: 1;
    vertical-align: -0.2em;
    letter-spacing: normal;
    text-transform: none;
    display: inline-block;
    white-space: nowrap;
    word-wrap: normal;
    direction: ltr;
    font-feature-settings: 'liga';
    -webkit-font-smoothing: antialiased;
}}

.stApp {{
    background: {c["bg"]} !important;
    color: {c["text"]};
}}

/* Top chrome: keep thin so less black bar; content padding clears overlap */
[data-testid="stHeader"] {{
    background: {c["bg"]} !important;
    border-bottom: 1px solid {c["border"]} !important;
    padding-top: 0.25rem !important;
    padding-bottom: 0.25rem !important;
    min-height: 0 !important;
    height: auto !important;
}}

[data-testid="stHeader"] > div {{
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}}

[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {c["sidebar_1"]} 0%, {c["sidebar_2"]} 100%) !important;
    border-right: 1px solid {c["border_strong"]} !important;
}}

[data-testid="stSidebar"] .block-container {{
    padding-top: 0.75rem;
}}

[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span,
[data-testid="stSidebar"] label {{
    color: {c["text"]} !important;
}}

[data-testid="stSidebar"] a {{
    color: {c["primary_light"]} !important;
}}

/* Push page content below fixed Streamlit header (avoids clipping hero/title) */
section[data-testid="stMain"] .main .block-container {{
    padding-top: 4.5rem !important;
    padding-bottom: 1.25rem !important;
}}

section[data-testid="stMain"] > div {{
    padding-top: 0 !important;
}}

[data-testid="stMarkdownContainer"] a {{
    color: {c["primary_light"]} !important;
}}

[data-testid="stMarkdownContainer"] strong {{
    color: {c["text"]} !important;
}}

[data-testid="stCaption"], .stCaption {{
    color: {c["text_muted"]} !important;
}}

/* Primary buttons */
.stButton > button[kind="primary"], div[data-testid="stButton"] > button[kind="primary"] {{
    background: linear-gradient(180deg, {c["primary_light"]} 0%, {c["primary_dark"]} 100%) !important;
    border: 1px solid {c["primary_dark"]} !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 14px rgba(37, 99, 235, 0.35) !important;
}}

.stButton > button[kind="primary"] p, div[data-testid="stButton"] > button[kind="primary"] p {{
    color: #ffffff !important;
}}

.stButton > button[kind="secondary"] {{
    background: {c["surface_elevated"]} !important;
    border-color: {c["border_strong"]} !important;
    color: {c["primary_light"]} !important;
}}

/* Radio navigation */
[data-testid="stSidebar"] [data-testid="stRadio"] label {{
    font-weight: 500 !important;
    color: {c["text"]} !important;
}}

[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"] {{
    border-radius: 8px !important;
    padding: 0.35rem 0.5rem !important;
    border-color: {c["border"]} !important;
}}

[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"][aria-checked="true"] {{
    background: {c["primary_soft"]} !important;
    border-color: {c["primary"]} !important;
}}

/* Metrics */
[data-testid="stMetric"] {{
    background: {c["surface_elevated"]};
    border: 1px solid {c["border_strong"]};
    border-radius: 12px;
    padding: 0.75rem 1rem !important;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.35);
}}

[data-testid="stMetric"] label {{
    color: {c["text_muted"]} !important;
}}

[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    color: {c["primary_light"]} !important;
}}

/* Section titles in main content */
section[data-testid="stMain"] h2,
section[data-testid="stMain"] h3,
section[data-testid="stMain"] h4 {{
    color: {c["text"]} !important;
}}

section[data-testid="stMain"] h2 {{
    color: {c["accent_light"]} !important;
}}

/* Header hero — room inside so h1 / icon ascenders are not clipped */
.main-header {{
    background: linear-gradient(135deg, {c["header_grad_1"]} 0%, {c["header_grad_2"]} 55%, #172554 100%);
    padding: 1.25rem 1.35rem 1rem 1.35rem;
    border-radius: 14px;
    color: {c["text"]};
    margin-bottom: 1rem;
    margin-top: 0;
    border: 1px solid {c["header_border"]};
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(96, 165, 250, 0.12);
    overflow: visible;
}}

.main-header-inner {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    flex-wrap: wrap;
    padding-top: 0.15rem;
}}

.main-header-icon {{
    font-size: 2.85rem !important;
    color: {c["primary_light"]};
    filter: drop-shadow(0 0 12px rgba(59, 130, 246, 0.45));
    line-height: 1 !important;
    margin-top: 0.1rem;
}}

.main-header-text {{
    text-align: center;
}}

.main-header h1 {{
    font-size: 1.5rem;
    font-weight: 700;
    margin: 0;
    padding-top: 0.15rem;
    line-height: 1.25;
    color: #f8fafc !important;
    letter-spacing: -0.02em;
}}

.main-header .main-header-sub {{
    margin: 0.4rem 0 0 0;
    color: {c["text_muted"]};
    font-size: 0.98rem;
    font-weight: 500;
}}

/* Sidebar small headings */
.sidebar-heading {{
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.95rem;
    font-weight: 600;
    color: {c["accent_light"]};
    margin: 0.5rem 0 0.35rem 0;
}}

.sidebar-heading .material-symbols-outlined {{
    font-size: 1.15rem;
    color: {c["primary_light"]};
}}

/* Widgets (sliders, selects) — dark surfaces */
[data-baseweb="select"] > div {{
    background-color: {c["surface_elevated"]} !important;
    border-color: {c["border_strong"]} !important;
}}

[data-testid="stSlider"] label, [data-testid="stSelectbox"] label, [data-testid="stMultiSelect"] label {{
    color: {c["text"]} !important;
}}

[data-testid="stExpander"] details {{
    background: {c["surface"]} !important;
    border: 1px solid {c["border"]} !important;
    border-radius: 10px !important;
}}

[data-testid="stExpander"] summary {{
    color: {c["text"]} !important;
}}

[data-testid="stChatMessage"] {{
    background: {c["surface"]} !important;
}}
</style>
"""


def inject_theme() -> None:
    import streamlit as st

    st.markdown(theme_css(), unsafe_allow_html=True)
