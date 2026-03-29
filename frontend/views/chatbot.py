import os
import streamlit as st

from county_data import fetch_county_names

API_URL = os.getenv("API_URL", "http://localhost:8000")


def show():
    st.subheader("💬 AI Disaster Assistant")
    st.markdown("Ask me anything about disaster preparedness, evacuation, or safety tips")

    counties = fetch_county_names(API_URL)
    selected_county = st.selectbox(
        "📍 Your Location (for personalized advice)",
        ["Select county"] + counties,
    )

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask about hurricanes, floods, evacuation..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response = generate_response(prompt, selected_county)
            st.markdown(response)
            st.session_state.chat_messages.append({"role": "assistant", "content": response})

def generate_response(prompt, county):
    prompt_lower = prompt.lower()

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

    elif any(word in prompt_lower for word in ["flood", "flooding"]):
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

    elif any(word in prompt_lower for word in ["evacuation", "evacuate", "zone"]):
        zones = {
            "Miami-Dade": "Zone A (Highest Risk)",
            "Broward": "Zone A (Highest Risk)",
            "Palm Beach": "Zone B",
            "Hillsborough": "Zone C",
            "Orange": "Zone D",
            "Duval": "Zone B"
        }

        zone_info = zones.get(county, "Check floridadisaster.org for your zone") if county != "Select county" else "Select your county for zone information"

        return f"""
**🚗 Evacuation Information**

**Your Zone:** {zone_info}

**Evacuation Checklist:**
- 🎒 Go-bag with essentials (clothes, meds, documents)
- 💊 7-day supply of medications
- 📱 Phone, charger, power bank
- 💧 Water and snacks
- 🗺️ Map with evacuation routes
- 🐕 Pet supplies if applicable

**Important:** Follow official evacuation orders immediately. Don't wait!
"""

    elif any(word in prompt_lower for word in ["kit", "supplies", "prepare", "emergency"]):
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

    else:
        return f"""
**🤖 Florida Disaster Assistant**

I can help you with:
- 🌪️ **Hurricanes** - Preparation, safety, recovery
- 💧 **Floods** - Safety tips, evacuation
- 🚗 **Evacuation** - Zones, planning, routes
- 📦 **Emergency Kit** - What to prepare
- 📍 **Your Location** - {county if county != "Select county" else "select your county for personalized info"}

**Try asking:**
- "What should I do during a hurricane?"
- "How to prepare for flooding?"
- "What's my evacuation zone?"
- "Emergency kit checklist"
"""
