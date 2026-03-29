import streamlit as st
import streamlit.components.v1 as components

from chatbot_context import load_context_for_location

# (short label, full text sent to the assistant) — shown as chips above the chat input
SUGGESTED_PROMPTS: tuple[tuple[str, str], ...] = (
    ("Go-bag essentials?", "What should I put in my go-bag for 3 days?"),
    ("Evacuation tips?", "How do I evacuate safely if ordered?"),
    ("48h before hurricane?", "What should I do 48 hours before a hurricane?"),
    ("Official alerts?", "Where can I get official alerts for my county?"),
    ("Hurricane prep?", "What should I do to prepare for a hurricane?"),
    ("Flood safety?", "How do I stay safe during flash flooding?"),
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
    """Single assistant message for this lat/lon (idempotent per coordinate key)."""
    key = f"{lat:.5f},{lon:.5f}"
    st.session_state.geo_lat = lat
    st.session_state.geo_lon = lon
    st.session_state.location_acquired = True
    if st.session_state.get("_geo_announce_key") == key:
        return

    md, _base, county = load_context_for_location(lat, lon)
    st.session_state.chat_messages.append({"role": "assistant", "content": md})
    st.session_state._geo_announce_key = key
    st.session_state.nearest_county = county


def _maybe_process_geo_url() -> None:
    """If URL has lat/lon (from Check location → full-page reload), add announcement."""
    qp = _get_query_params()
    lat = _parse_float_q(qp.get("lat"))
    lon = _parse_float_q(qp.get("lon"))
    if lat is None or lon is None:
        return
    _apply_geo_announcement(lat, lon)


def generate_response(prompt: str, county: str | None) -> str:
    prompt_lower = prompt.lower()
    county_label = county or "your area"

    if any(word in prompt_lower for word in ["hurricane", "storm", "cyclone"]):
        return """
**🌀 Hurricane Preparedness Guide**

**Before Hurricane:**
- 📦 Stock emergency supplies (3-7 days)
- 🪟 Secure windows and doors with shutters
- 🔋 Charge all devices and power banks
- 🚗 Fill gas tank
- 📝 Gather important documents

**During Hurricane:**
- 🏠 Stay indoors away from windows
- 📻 Monitor official updates
- 🚫 Do not go outside

**After Hurricane:**
- ⚠️ Check for hazards before leaving
- 📞 Report damage to authorities
- 💧 Boil water until advised safe
"""

    if any(word in prompt_lower for word in ["flood", "flooding"]):
        return """
**💧 Flood Safety Guide**

**Before Flood:**
- 📦 Move valuables to higher ground
- 🔌 Turn off electricity if water rises
- 🚗 Prepare to evacuate if needed

**During Flood:**
- 🏔️ Move to higher ground immediately
- 🚫 NEVER drive through flood water
- 🚶‍♂️ Do not walk through moving water

**After Flood:**
- ⚠️ Avoid floodwater (contaminated)
- 📞 Wait for official "all clear"
- 🧹 Document damage for insurance
"""

    if any(word in prompt_lower for word in ["evacuation", "evacuate", "zone"]):
        return f"""
**🚗 Evacuation Information**

**Your area:** {county_label} — follow **FDEM** and your **county emergency management** for evacuation zones and orders.

**Evacuation Checklist:**
- 🎒 Go-bag with essentials (clothes, meds, documents)
- 💊 7-day supply of medications
- 📱 Phone, charger, power bank
- 💧 Water and snacks
- 🗺️ Map with evacuation routes
- 🐕 Pet supplies if applicable

**Important:** Follow official evacuation orders immediately. Don't wait!
"""

    if any(
        word in prompt_lower
        for word in ["kit", "supplies", "prepare", "emergency", "go-bag", "go bag"]
    ):
        return """
**📦 Emergency Kit Checklist**

**Water & Food:**
- 💧 1 gallon water per person per day (3-7 days)
- 🍫 Non-perishable food (3-7 days)
- 🥫 Manual can opener

**Tools & Supplies:**
- 🔦 Flashlight with extra batteries
- 📻 Battery-powered radio
- 🔋 Power bank for phones
- 🗺️ Local maps
- 📝 Important documents (IDs, insurance)

**Health & Safety:**
- 💊 Prescription medications (7-day supply)
- 🩹 First aid kit
- 🪥 Personal hygiene items
- 😷 Masks and sanitizer

**Special Items:**
- 🐕 Pet supplies if applicable
- 👶 Baby supplies if applicable
- 👴 Elderly care items if applicable
"""

    if any(
        word in prompt_lower
        for word in ["alert", "official", "warning", "watch", "noaa", "nws", "county"]
    ):
        return f"""
**📢 Official information**

- **NWS:** [weather.gov](https://www.weather.gov/) — alerts and warnings for **{county_label}**
- **NHC:** [nhc.noaa.gov](https://www.nhc.noaa.gov/) — tropical cyclones
- **Florida:** [floridadisaster.org](https://www.floridadisaster.org/) — state guidance

Use **local county** emergency management and **FEMA app** where available. Your **status check** above uses the same API feeds as the Risk Map and Ocean Tracker when the backend is running.
"""

    return f"""
**🤖 Florida Disaster Assistant**

I can help with:
- 🌪️ **Hurricanes** — preparation, safety, recovery
- 💧 **Floods** — safety tips, evacuation
- 🚗 **Evacuation** — planning and routes
- 📦 **Emergency kit** — what to prepare
- 📍 **Your area:** {county_label}

**Try asking:**
- "What should I do during a hurricane?"
- "How to prepare for flooding?"
- "What's in a good go-bag?"
"""


def _assistant_header() -> None:
    st.subheader("💬 AI Disaster Assistant")
    st.markdown(
        "Ask about disaster preparedness, evacuation, or safety tips. "
        "Your **area status** in the chat uses **Risk Map** + **Ocean** API data when the backend is running."
    )


def _render_geo_only() -> None:
    """Browser geolocation control (shown below assistant header until location is set)."""
    components.html(_GEO_HTML, height=140)


def _inject_chat_layout_css() -> None:
    """Reserve vertical space so suggestion chips are not covered by Streamlit's fixed chat input."""
    st.markdown(
        """
<style>
  section[data-testid="stMain"] .block-container,
  section.main .block-container {
    padding-bottom: max(20rem, 42vh) !important;
  }
</style>
        """,
        unsafe_allow_html=True,
    )


def _append_qa_if_new(user_text: str, reply: str) -> None:
    """Append one user + assistant pair unless the chat already ends with this exact pair (stops rerun loops)."""
    msgs = st.session_state.chat_messages
    if len(msgs) >= 2:
        u, a = msgs[-2], msgs[-1]
        if (
            u.get("role") == "user"
            and a.get("role") == "assistant"
            and u.get("content") == user_text
            and a.get("content") == reply
        ):
            return
    st.session_state.chat_messages.append({"role": "user", "content": user_text})
    st.session_state.chat_messages.append({"role": "assistant", "content": reply})


def _render_suggested_prompt_row() -> None:
    """One click appends Q&A; _append_qa_if_new prevents duplicate pairs if Streamlit replays a run."""
    county = st.session_state.get("nearest_county")
    n = len(SUGGESTED_PROMPTS)
    mid = (n + 1) // 2
    row1 = st.columns(mid)
    for i in range(mid):
        short_lbl, full_q = SUGGESTED_PROMPTS[i]
        with row1[i]:
            if st.button(short_lbl, key=f"sq_{i}", use_container_width=True):
                reply = generate_response(full_q, county)
                _append_qa_if_new(full_q, reply)
    if n > mid:
        row2 = st.columns(n - mid)
        for j, i in enumerate(range(mid, n)):
            short_lbl, full_q = SUGGESTED_PROMPTS[i]
            with row2[j]:
                if st.button(short_lbl, key=f"sq_{i}", use_container_width=True):
                    reply = generate_response(full_q, county)
                    _append_qa_if_new(full_q, reply)


def show():
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    _maybe_process_geo_url()

    if not st.session_state.get("location_acquired"):
        _assistant_header()
        _render_geo_only()
        return

    _assistant_header()
    _inject_chat_layout_css()

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    with st.container():
        _render_suggested_prompt_row()

    if prompt := st.chat_input("Ask about hurricanes, floods, evacuation..."):
        text = prompt.strip()
        if text:
            county = st.session_state.get("nearest_county")
            response = generate_response(text, county)
            _append_qa_if_new(text, response)
