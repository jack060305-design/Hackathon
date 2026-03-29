# Florida Disaster Risk Platform

A small **Florida-focused** web app that combines **hazard maps**, a **tropical/ocean outlook** view, and an **AI assistant** powered by **Google Gemini**. The backend exposes a FastAPI service for data and chat; the frontend is **Streamlit**.

**Important:** Map and forecast numbers come from your APIs and data sources. The chatbot uses an LLM for **guidance and general preparedness** only—it is not a substitute for official alerts or emergency services.

---

## Features

- **Risk Map** — Inland-style risk markers (e.g. USGS / NWS-related pipelines exposed by the backend).
- **Ocean Tracker** — Short-horizon tropical / marine-style outlook for Florida when the backend has data.
- **AI Assistant** — Chat with **Gemini** via `POST /api/chat`. After **Check location**, the app loads hazard context from the backend, sends a **one-time** summary prompt to Gemini, then waits for your questions or suggested prompts.
- **Geolocation** — Browser `navigator.geolocation` + full-page navigation with `lat` / `lon` query parameters (see the AI Assistant page).

---

## Repository layout

| Path | Role |
|------|------|
| `backend/` | FastAPI app (`app.main:app`), Gemini chat service, disaster / ocean / prediction routes |
| `frontend/` | Streamlit app (`app.py`), map / ocean / chatbot views, `chatbot_context.py` |
| `data/` | GeoJSON and fallback JSON used by the backend/frontend |
| `mcp_server/` | Optional MCP bridge (separate requirements) |
| `scripts/` | Small verification helpers |
| `run-project.ps1` | Windows: free ports, start API + Streamlit |

---

## Prerequisites

- **Python 3.10+** (3.11 works with the pinned stacks in this repo).
- A **Gemini API key** from [Google AI Studio](https://aistudio.google.com/apikey) for chat.

---

## Quick start (Windows)

From the repo root:

```powershell
.\run-project.ps1
```

This stops common dev ports, then starts:

- **API:** http://127.0.0.1:8000 — OpenAPI at `/docs`
- **Streamlit:** http://127.0.0.1:8888

Close the two PowerShell windows it opens to stop the servers.

---

## Manual setup

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env` (never commit real keys; this file is gitignored):

```env
GEMINI_API_KEY=your_key_here
```

Copy from `backend/.env.example` for optional tuning (`GEMINI_MODEL`, token caps, etc.).

Run the API:

```powershell
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check: http://127.0.0.1:8000/health

### 2. Frontend

```powershell
cd frontend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Optional: point the UI at a non-default API (defaults to `http://127.0.0.1:8000`):

```powershell
$env:API_URL = "http://127.0.0.1:8000"
```

Run Streamlit:

```powershell
cd frontend
python -m streamlit run app.py --server.port 8888
```

---

## Environment variables

| Variable | Where | Purpose |
|----------|--------|---------|
| `GEMINI_API_KEY` | `backend/.env` | Required for `/api/chat` |
| `GEMINI_MODEL`, `GEMINI_CHAT_MAX_MESSAGES`, `GEMINI_MAX_MESSAGE_CHARS`, `GEMINI_MAX_OUTPUT_TOKENS` | `backend/.env` | Optional; see `backend/.env.example` |
| `API_URL` | Frontend shell env | Base URL for the FastAPI backend |

---

## API overview

- `GET /health` — Liveness.
- `GET /docs` — Swagger UI.
- `POST /api/chat` — Body: `{ "messages": [{ "role": "user"|"assistant", "content": "..." }], "county": "optional" }`. Returns `{ "reply": "..." }`.
- Disaster / ocean / prediction routes under `/api/disasters`, `/api/ocean`, `/api/prediction` (see `/docs`).

---

## Development notes

- **Chat** — The Streamlit chatbot avoids sending duplicate turns on rerun by queuing user input with `on_submit` / `on_click` and processing one pending message per run.
- **Sidebar + geo URL** — Opening the app with `lat`, `lon`, or `nav=ai` selects the AI page **once** per URL signature so the sidebar is not forced back to AI on every interaction.
- **Verify** — See `scripts/verify.py` if you extend CI or smoke checks.

---

## License / attribution

Built as a hackathon project. Data feeds and trademarks (USGS, NOAA, NWS, etc.) belong to their respective owners; follow each source’s terms when redistributing or deploying publicly.
