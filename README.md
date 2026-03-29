# Florida Disaster Risk Prediction

A **Florida-focused** web app that brings together **inland hazard maps**, a **7-day ocean / tropical outlook**, and an **AI assistant** powered by **Google Gemini**. The **FastAPI** backend serves data and chat; the **Streamlit** frontend provides maps and the conversational UI.

> **Disclaimer:** Map and forecast values come from integrated feeds and backend logic (USGS, NWS, NHC-related pipelines, etc.). The assistant uses an LLM for **general preparedness and education** only—it is **not** a substitute for **911**, **NWS**, **county emergency management**, or **official evacuation orders**.

---

## Features

| Area | What it does |
|------|----------------|
| **Risk Map** | Inland hazard markers (USGS + NWS-style data via the API, with direct-feed fallback). |
| **Ocean Tracker** | ~7-day tropical outlook for Florida when the backend has storm data. |
| **AI Assistant** | Chat through `POST /api/chat` (Gemini). **Check location** uses browser geolocation, then loads hazard context for a one-time summary before your questions. |
| **Geolocation** | `navigator.geolocation` plus full-page reload with `lat`, `lon`, and `nav=ai` query params. |

---

## Tech stack

- **Backend:** FastAPI, Uvicorn, Pydantic, `httpx`, `google-generativeai`, optional scikit-learn for risk scoring  
- **Frontend:** Streamlit, Folium, `streamlit-folium`, shared **`frontend/theme.py`** (Plus Jakarta Sans + Material Symbols, dark blue/black UI)  
- **Optional:** `mcp_server/` (MCP bridge for IDE tools — separate `requirements.txt`)

---

## Repository layout

| Path | Role |
|------|------|
| `backend/` | FastAPI (`uvicorn app.main:app`), chat, disasters, ocean, prediction routes |
| `frontend/` | Streamlit entry `app.py`, views (`map`, `ocean_tracker`, `chatbot`), `theme.py`, `chatbot_context.py` |
| `data/` | GeoJSON and fallback JSON for maps |
| `mcp_server/` | Optional MCP server |
| `scripts/` | Verification helpers |
| `run-project.ps1` | Windows: frees dev ports, starts API **:8000** + Streamlit **:8888** |
| `run-project.bat` | Wrapper that calls `run-project.ps1` |

---

## Prerequisites

- **Python 3.10 – 3.13** (`backend/requirements.txt` uses compatible lower bounds; use a venv per service.)  
- **Gemini API key** — [Google AI Studio](https://aistudio.google.com/apikey) for `/api/chat`

---

## Quick start (Windows)

From the **repository root** (folder that contains `run-project.ps1`):

```powershell
.\run-project.ps1
```

Or double-click **`run-project.bat`** (opens a console and runs the same script).

This stops processes on common dev ports, then starts:

- **API:** http://127.0.0.1:8000 — Swagger UI at `/docs`  
- **Streamlit:** http://127.0.0.1:8888  

Close the two PowerShell windows that open to stop both servers.

---

## Manual setup

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Create **`backend/.env`** (file is **gitignored** — do not commit keys):

```env
GEMINI_API_KEY=your_key_here
```

Copy from **`backend/.env.example`** for optional variables (`GEMINI_MODEL`, message/token limits).

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health: http://127.0.0.1:8000/health  

### 2. Frontend

```powershell
cd frontend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Optional — non-default API URL:

```powershell
$env:API_URL = "http://127.0.0.1:8000"
python -m streamlit run app.py --server.port 8888
```

### macOS / Linux

Same steps with `source .venv/bin/activate` and run `uvicorn` / `streamlit` from `backend/` and `frontend/` respectively. There is no `run-project.sh`; use two terminals or a process manager.

---

## Environment variables

| Variable | Where | Purpose |
|----------|--------|---------|
| `GEMINI_API_KEY` | `backend/.env` | Required for **`POST /api/chat`** |
| `GEMINI_MODEL`, `GEMINI_CHAT_MAX_MESSAGES`, `GEMINI_MAX_MESSAGE_CHARS`, `GEMINI_MAX_OUTPUT_TOKENS` | `backend/.env` | Optional; see `.env.example` |
| `API_URL` | Frontend environment | Base URL for the API (default `http://127.0.0.1:8000`) |

---

## API highlights

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/health` | Liveness |
| `GET` | `/docs` | OpenAPI UI |
| `POST` | `/api/chat` | Body: `{ "messages": [...], "county": "optional" }` → `{ "reply": "..." }` |
| `GET` | `/api/disasters/*`, `/api/ocean/*`, `/api/prediction/*` | See `/docs` for full list |

---

## Troubleshooting

| Issue | What to try |
|--------|-------------|
| **Chat returns 503** | Set `GEMINI_API_KEY` in `backend/.env` and restart Uvicorn |
| **Maps / API 404** | Ensure **one** Hackathon API is listening on **8000**; run Uvicorn from **`backend/`** |
| **Port in use** | Run `run-project.ps1` again, or `netstat` / Task Manager to free **8000** / **8888** |
| **Streamlit theme** | Uses `frontend/.streamlit/config.toml` + `theme.py`; hard refresh the browser (**Ctrl+Shift+R**) |

---

## Development notes

- Chat avoids duplicate LLM turns on Streamlit rerun by queuing input with `on_submit` / `on_click`.  
- Sidebar syncs with geo URLs (`lat`, `lon`, `nav=ai`) once per URL signature so navigation does not reset every interaction.  
- **`scripts/verify.py`** — useful for smoke checks or CI.

---

## License / attribution

Hackathon project. Data sources and names (**USGS**, **NOAA**, **NWS**, **NHC**, etc.) belong to their respective owners; follow each provider’s terms for public deployment.
