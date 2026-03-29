import streamlit as st


def show():
    st.markdown(
        '<p class="section-title">AI Disaster Assistant</p>', unsafe_allow_html=True
    )
    st.caption(
        "Ask About Preparedness, Evacuation, Or Safety—Rule-Based Guidance For Demo Purposes."
    )

    with st.container(border=True):
        selected_county = st.selectbox(
            "Your County (For Localized Tips)",
            ["Select County"]
            + [
                "Miami-Dade",
                "Broward",
                "Palm Beach",
                "Hillsborough",
                "Orange",
                "Duval",
            ],
        )

        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []

        for message in st.session_state.chat_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input(
            "Ask About Hurricanes, Floods, Evacuation, Or Emergency Kits…"
        ):
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                response = generate_response(prompt, selected_county)
                st.markdown(response)
                st.session_state.chat_messages.append(
                    {"role": "assistant", "content": response}
                )


def generate_response(prompt, county):
    prompt_lower = prompt.lower()

    if any(word in prompt_lower for word in ["hurricane", "storm", "cyclone"]):
        return """
**Hurricane Preparedness Guide**

**Before The Storm**
- Stock Emergency Supplies (Three To Seven Days)
- Secure Windows And Doors With Shutters
- Charge Devices And Power Banks
- Fill Your Gas Tank
- Gather Important Documents

**During The Storm**
- Stay Indoors Away From Windows
- Monitor Official Updates
- Do Not Go Outside

**After The Storm**
- Check For Hazards Before Leaving
- Report Damage To Authorities
- Boil Water Until Officials Say It Is Safe
"""

    elif any(word in prompt_lower for word in ["flood", "flooding"]):
        return """
**Flood Safety Guide**

**Before Flooding**
- Move Valuables To Higher Ground
- Turn Off Electricity If Water Rises
- Prepare To Evacuate If Needed

**During Flooding**
- Move To Higher Ground Immediately
- Never Drive Through Flood Water
- Do Not Walk Through Moving Water

**After Flooding**
- Avoid Floodwater (May Be Contaminated)
- Wait For The Official All Clear
- Document Damage For Insurance
"""

    elif any(word in prompt_lower for word in ["evacuation", "evacuate", "zone"]):
        zones = {
            "Miami-Dade": "Zone A (Highest Risk)",
            "Broward": "Zone A (Highest Risk)",
            "Palm Beach": "Zone B",
            "Hillsborough": "Zone C",
            "Orange": "Zone D",
            "Duval": "Zone B",
        }

        zone_info = (
            zones.get(county, "Check floridadisaster.org For Your Zone")
            if county != "Select County"
            else "Select Your County For Zone Information"
        )

        return f"""
**Evacuation Information**

**Your Zone:** {zone_info}

**Evacuation Checklist**
- Go-Bag With Essentials (Clothes, Meds, Documents)
- Seven-Day Supply Of Medications
- Phone, Charger, Power Bank
- Water And Snacks
- Map With Evacuation Routes
- Pet Supplies If Applicable

**Important:** Follow Official Evacuation Orders Immediately—Do Not Wait.
"""

    elif any(
        word in prompt_lower for word in ["kit", "supplies", "prepare", "emergency"]
    ):
        return """
**Emergency Kit Checklist**

**Water And Food**
- One Gallon Water Per Person Per Day (Three To Seven Days)
- Non-Perishable Food (Three To Seven Days)
- Manual Can Opener

**Tools And Supplies**
- Flashlight With Extra Batteries
- Battery-Powered Radio
- Power Bank For Phones
- Local Maps
- Important Documents (IDs, Insurance)

**Health And Safety**
- Prescription Medications (Seven-Day Supply)
- First Aid Kit
- Personal Hygiene Items
- Masks And Sanitizer

**Special Items**
- Pet Supplies If Applicable
- Baby Supplies If Applicable
- Elder Care Items If Applicable
"""

    else:
        loc = (
            county
            if county != "Select County"
            else "Select Your County For Personalized Info"
        )
        return f"""
**Florida Disaster Assistant**

I Can Help With:
- **Hurricanes** — Preparation, Safety, Recovery
- **Floods** — Safety Tips And Evacuation
- **Evacuation** — Zones, Planning, Routes
- **Emergency Kits** — What To Pack
- **Your Location** — {loc}

**Try Asking**
- "What Should I Do During A Hurricane?"
- "How Do I Prepare For Flooding?"
- "What Is My Evacuation Zone?"
- "Emergency Kit Checklist"
"""
