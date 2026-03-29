import os

import requests
import streamlit as st
import streamlit.components.v1 as components

from chatbot_context import load_context_for_location

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")

_GEO_LLM_USER_LABEL = "📍 Check location & hazard context"

_GEO_ANNOUNCE_INSTRUCTION = """The user just used "Check location" in the app. Below is **app-loaded** Florida hazard/status context from backend APIs (Risk Map / ocean outlook — not something you fetched yourself).

---
{md}
---

Give one **short** assistant opening in Markdown (about 4–8 lines): welcome them, mention county or area if clear, summarize what matters for preparedness from this context, and point to official sources (NWS, county EM, FloridaDisaster.org) for live orders. Synthesize; do not paste the raw context back verbatim."""

# (short label, full prompt sent to Gemini) — full strings are explicit so the model answers well
SUGGESTED_PROMPTS: tuple[tuple[str, str], ...] = (
    (
        "Go-bag (3 days)",
        "I am preparing for hurricanes in Florida. List specific items for a **3-day emergency go-bag** "
        "for one adult, grouped by category (water, food, medications, documents, tools, hygiene). "
        "Add a short note on pets if relevant. Use bullet points.",
    ),
    (
        "Evacuation order",
        "Explain what I should do if **local officials issue an evacuation order** in Florida: "
        "how to decide timing, what to bring, route planning, and common mistakes to avoid. "
        "Keep it practical and mention following county EM and law enforcement.",
    ),
    (
        "48h before hurricane",
        "What should I prioritize in the **48 hours before a hurricane** makes landfall in Florida? "
        "Give a prioritized checklist (home, supplies, documents, vehicle, communication).",
    ),
    (
        "Official alerts",
        "Where should I get **official weather and evacuation alerts** for my Florida county? "
        "Name types of sources (NWS, county EM, state) and what to avoid (rumors).",
    ),
    (
        "Hurricane prep",
        "Give a **concise hurricane preparedness overview** for a Florida household: "
        "home hardening, insurance docs, medical needs, and when to shelter in place vs evacuate.",
    ),
    (
        "Flash flood safety",
        "What are the top **flash flood safety rules** for Florida (driving, walking, storm surge vs rainfall)? "
        "Use clear do / don't bullets.",
    ),
)

# Browser Geolocation API: getLocation() → getCurrentPosition(successCb, errorCb, options)
# https://developer.mozilla.org/en-US/docs/Web/API/Geolocation_API
# st.components.html runs in a sandboxed srcdoc iframe (no allow-top-navigation). Navigating
# the tab from *inside* that iframe is blocked. Workaround: create <a target="_top"> in
# window.parent.document and .click() it (same idea as streamlit/streamlit#6922).
_GEO_HTML = """
<div style="font-family: system-ui, sans-serif; display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:4rem;">
  <button type="button" onclick="getLocation()" style="
    background: linear-gradient(180deg, #5eb8d9 0%, #3d9bb8 100%);
    color: white; border: none; padding: 0.65rem 1.35rem;
    border-radius: 10px; font-weight: 600; cursor: pointer; font-size: 1rem;
    box-shadow: 0 2px 8px rgba(30,100,130,0.25);
  ">📍 Check location / status</button>
  <p id="geo-msg" style="margin-top:0.55rem;color:#555;font-size:0.88rem;max-width:36rem;text-align:center;"></p>
</div>
<script>
var geoOptions = {
  enableHighAccuracy: false,
  timeout: 20000,
  maximumAge: 300000
};

function resolveAppUrl() {
  try {
    if (window.parent && window.parent !== window) {
      var h = window.parent.location.href;
      if (h && h.indexOf('http') === 0) {
        return new URL(h);
      }
    }
  } catch (e) {}
  try {
    if (document.referrer && document.referrer.indexOf('http') === 0) {
      return new URL(document.referrer);
    }
  } catch (e2) {}
  return null;
}

function navigateTopWithParams(lat, lon) {
  var msg = document.getElementById('geo-msg');
  var u = resolveAppUrl();
  if (!u) {
    msg.innerHTML = 'Could not resolve app URL. Refresh the page and try again.';
    return;
  }
  u.searchParams.set('lat', lat);
  u.searchParams.set('lon', lon);
  u.searchParams.set('geo', '1');
  u.searchParams.set('nav', 'ai');
  var href = u.toString();

  function clickTopFromParentDoc(doc) {
    var a = doc.createElement('a');
    a.href = href;
    a.target = '_top';
    a.rel = 'noopener noreferrer';
    a.style.display = 'none';
    doc.body.appendChild(a);
    a.click();
    doc.body.removeChild(a);
  }

  try {
    if (window.parent && window.parent !== window && window.parent.document && window.parent.document.body) {
      clickTopFromParentDoc(window.parent.document);
      return;
    }
  } catch (e1) {}

  try {
    if (window.top && window.top !== window && window.top.document && window.top.document.body) {
      clickTopFromParentDoc(window.top.document);
      return;
    }
  } catch (e2) {}

  msg.innerHTML = 'Open this link to apply your location (sandbox blocked auto-redirect):<br/>'
    + '<a href="' + href.replace(/"/g, '&quot;') + '" target="_blank" rel="noopener">Open in new tab</a>';
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(href).then(function() {
      msg.innerHTML += '<br/><span style="color:#0a7;">Link copied — paste in the address bar if needed.</span>';
    }).catch(function() {});
  }
}

/**
 * Same idea as MDN/W3Schools: two callbacks only — (position) => { ... }, (err) => { ... }
 * Do not use ((position) => ...) — extra "(" breaks the parser.
 * Third argument is optional PositionOptions (timeout, maximumAge, enableHighAccuracy).
 */
function getLocation() {
  var x = document.getElementById('geo-msg');
  if (navigator.geolocation) {
    x.innerHTML = 'Requesting location…';
    navigator.geolocation.getCurrentPosition(
      (position) => {
        console.log(position.coords.latitude, position.coords.longitude);
        var lat = position.coords.latitude.toFixed(6);
        var lon = position.coords.longitude.toFixed(6);
        navigateTopWithParams(lat, lon);
      },
      (err) => {
        alert(err.message);
        var codes = {1: 'PERMISSION_DENIED', 2: 'POSITION_UNAVAILABLE', 3: 'TIMEOUT'};
        var name = codes[err.code] || ('code_' + err.code);
        x.innerHTML = 'Geolocation: ' + name + ' — ' + (err.message || '');
      },
      geoOptions
    );
  } else {
    alert('Geolocation is not supported by this browser');
    x.innerHTML = 'Geolocation is not supported by this browser.';
  }
}
</script>
"""


def _get_query_params() -> dict:
    try:
        qp = st.query_params
        out = {}
        for k in qp.keys():
            v = qp.get(k)
            if isinstance(v, list):
                out[k] = v
            elif v is None:
                out[k] = []
            else:
                out[k] = [v]
        return out
    except Exception:
        return st.experimental_get_query_params()


def _parse_float_q(val) -> float | None:
    if val is None:
        return None
    if isinstance(val, (list, tuple)) and val:
        s = val[0]
    else:
        s = val
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _apply_geo_announcement(lat: float, lon: float) -> None:
    """Load API hazard context, county, and queue one LLM announce turn (idempotent per coordinate key)."""
    key = f"{lat:.5f},{lon:.5f}"
    st.session_state.geo_lat = lat
    st.session_state.geo_lon = lon
    st.session_state.location_acquired = True
    if st.session_state.get("_geo_llm_announced_key") == key:
        return

    md, _, county = load_context_for_location(lat, lon)
    st.session_state.nearest_county = county
    st.session_state["_pending_geo_llm"] = {"md": md, "county": county, "key": key}


def _maybe_process_geo_url() -> None:
    """If URL has lat/lon (from Check location → full-page reload), add announcement."""
    qp = _get_query_params()
    lat = _parse_float_q(qp.get("lat"))
    lon = _parse_float_q(qp.get("lon"))
    if lat is None or lon is None:
        return
    _apply_geo_announcement(lat, lon)


def _normalize_turn_text(s: str) -> str:
    """Stable compare for chat turns (Streamlit/chat_input vs stored history)."""
    return (s or "").replace("\r\n", "\n").strip()


def _tail_already_answered(user_text: str) -> bool:
    """
    True if the last messages are already user (this prompt) + assistant.
    st.chat_input keeps returning the submitted string on later reruns; skip duplicate API/UI turns.
    """
    norm = _normalize_turn_text(user_text)
    if not norm:
        return False
    msgs = st.session_state.chat_messages
    if len(msgs) < 2:
        return False
    u, a = msgs[-2], msgs[-1]
    return (
        u.get("role") == "user"
        and a.get("role") == "assistant"
        and _normalize_turn_text(u.get("content") or "") == norm
    )


def _post_chat_messages(payload_messages: list[dict], county: str | None) -> str:
    """POST `/api/chat` once; returns assistant text or a markdown error message."""
    try:
        r = requests.post(
            f"{API_URL}/api/chat",
            json={"messages": payload_messages, "county": county},
            timeout=120,
        )
        if r.status_code == 503:
            return (
                "**AI is not configured on the server.**\n\n"
                "Set `GEMINI_API_KEY` in the backend environment (e.g. `backend/.env`) and restart the API. "
                "See [Google AI Studio](https://aistudio.google.com/apikey) for a key."
            )
        if r.status_code == 429:
            try:
                err = r.json().get("detail", r.text)
            except Exception:
                err = r.text
            return f"**Gemini rate limit / quota**\n\n{err}"
        if not r.ok:
            try:
                err = r.json().get("detail", r.text)
            except Exception:
                err = r.text or r.reason
            return f"**API error ({r.status_code})**\n\n{err}"
        data = r.json()
        reply = (data.get("reply") or "").strip()
        return reply or "_Empty response from model._"
    except requests.HTTPError as e:
        resp = e.response
        detail = ""
        if resp is not None:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text or str(e)
        return f"**API error**\n\n{detail}"
    except requests.RequestException as e:
        return (
            f"**Could not reach the AI service** at `{API_URL}`.\n\n"
            f"`{e}`\n\n"
            "Start the backend from `backend/` and check that `/health` responds."
        )


def generate_response(prompt: str, county: str | None) -> str:
    """Gemini reply via backend `/api/chat` (API key stays on server)."""
    prompt_n = _normalize_turn_text(prompt)
    base = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.chat_messages
        if m.get("role") in ("user", "assistant")
    ]
    # Phantom resubmit: history already ends with this question + answer — do not call the API again.
    if (
        len(base) >= 2
        and base[-2].get("role") == "user"
        and base[-1].get("role") == "assistant"
        and _normalize_turn_text(base[-2].get("content") or "") == prompt_n
    ):
        return (base[-1].get("content") or "").strip()

    return _post_chat_messages([*base, {"role": "user", "content": prompt_n}], county)


def _run_geo_llm_announce_if_pending() -> None:
    """After Check location: one LLM call with API hazard markdown, then append short user label + assistant reply."""
    geo = st.session_state.pop("_pending_geo_llm", None)
    if not geo:
        return
    md = (geo.get("md") or "").strip() or "_No hazard context returned._"
    county = geo.get("county")
    key = geo.get("key")
    user_content = _GEO_ANNOUNCE_INSTRUCTION.format(md=md)
    if _tail_already_answered(_GEO_LLM_USER_LABEL):
        if key:
            st.session_state._geo_llm_announced_key = key
        st.session_state._chat_input_key = int(st.session_state.get("_chat_input_key", 0)) + 1
        return
    with st.spinner("Summarizing your location with Gemini…"):
        reply = _post_chat_messages([{"role": "user", "content": user_content}], county)
    st.session_state.chat_messages.append({"role": "user", "content": _GEO_LLM_USER_LABEL})
    st.session_state.chat_messages.append({"role": "assistant", "content": reply})
    if key:
        st.session_state._geo_llm_announced_key = key
    st.session_state._chat_input_key = int(st.session_state.get("_chat_input_key", 0)) + 1


def _assistant_header() -> None:
    st.subheader("💬 AI Disaster Assistant")
    st.markdown("Answers are generated by **Google Gemini** (via your API).")


def _render_geo_only() -> None:
    """Browser geolocation control (shown below assistant header until location is set)."""
    components.html(_GEO_HTML, height=140)


def _inject_chat_layout_css() -> None:
    """Reserve space for Streamlit fixed chat input; keep button styles scoped to main."""
    st.markdown(
        """
<style>
  section[data-testid="stMain"] .block-container,
  section.main .block-container {
    padding-bottom: max(22rem, 42vh) !important;
    margin-bottom: 1rem !important;
  }
  section[data-testid="stMain"] .block-container .stButton > button {
    background: linear-gradient(180deg, #3d9bb8 0%, #2d7a94 100%) !important;
    border: 1px solid #256f87 !important;
    color: #ffffff !important;
    position: relative !important;
    z-index: 1 !important;
  }
  section[data-testid="stMain"] .block-container .stButton > button p {
    color: #ffffff !important;
  }
</style>
        """,
        unsafe_allow_html=True,
    )


def _queue_chat_turn(text: str) -> None:
    """Queue a single user turn (processed once at top of show())."""
    t = _normalize_turn_text(text)
    if t:
        st.session_state["_chat_pending"] = t


def _on_chat_submit() -> None:
    key = st.session_state.get("_chat_widget_key")
    if not key:
        return
    raw = st.session_state.get(key)
    if isinstance(raw, str):
        _queue_chat_turn(raw)


def _run_one_llm_turn_if_pending() -> None:
    """
    One question → one LLM call → append user + assistant → bump chat key.
    Uses a queue so st.chat_input's return value is never used (avoids repeat submits on rerun).
    """
    pending = st.session_state.pop("_chat_pending", None)
    if pending is None:
        return
    user_part = _normalize_turn_text(pending)
    if not user_part:
        return
    if _tail_already_answered(user_part):
        st.session_state._chat_input_key = int(st.session_state.get("_chat_input_key", 0)) + 1
        return
    county = st.session_state.get("nearest_county")
    with st.spinner("Gemini is thinking…"):
        reply = generate_response(user_part, county)
    st.session_state.chat_messages.append({"role": "user", "content": user_part})
    st.session_state.chat_messages.append({"role": "assistant", "content": reply})
    st.session_state._chat_input_key = int(st.session_state.get("_chat_input_key", 0)) + 1


def _render_suggested_prompt_row() -> None:
    n = len(SUGGESTED_PROMPTS)
    mid = (n + 1) // 2
    row1 = st.columns(mid)
    for i in range(mid):
        short_lbl, full_q = SUGGESTED_PROMPTS[i]
        with row1[i]:
            st.button(
                short_lbl,
                key=f"sq_{i}",
                type="primary",
                use_container_width=True,
                on_click=_queue_chat_turn,
                args=(full_q,),
            )
    if n > mid:
        row2 = st.columns(n - mid)
        for j, i in enumerate(range(mid, n)):
            short_lbl, full_q = SUGGESTED_PROMPTS[i]
            with row2[j]:
                st.button(
                    short_lbl,
                    key=f"sq_{i}",
                    type="primary",
                    use_container_width=True,
                    on_click=_queue_chat_turn,
                    args=(full_q,),
                )


def show():
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "_chat_input_key" not in st.session_state:
        st.session_state._chat_input_key = 0

    _maybe_process_geo_url()

    if not st.session_state.get("location_acquired"):
        _assistant_header()
        _render_geo_only()
        return

    _assistant_header()
    _inject_chat_layout_css()

    _run_geo_llm_announce_if_pending()
    _run_one_llm_turn_if_pending()

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    with st.container():
        _render_suggested_prompt_row()

    chat_key = f"user_chat_{st.session_state._chat_input_key}"
    st.session_state["_chat_widget_key"] = chat_key
    st.chat_input(
        "Ask about hurricanes, floods, evacuation...",
        key=chat_key,
        on_submit=_on_chat_submit,
    )
