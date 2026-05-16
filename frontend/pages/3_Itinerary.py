"""Day itinerary — multiple stops in order."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import folium
from streamlit_folium import st_folium

from frontend import api_client as api

st.set_page_config(page_title="Itinerary — OnePick", page_icon="🗺️", layout="centered")

css = (Path(__file__).parent.parent / "style.css").read_text()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

if not api.is_logged_in():
    st.warning("Please log in from the main page.")
    st.stop()

st.title("Build a day 🗺️")
st.caption("Tell us a few moods. We'll route them in order.")

city = st.text_input("City", value="Iași")
cats = st.multiselect(
    "What's your day like?",
    options=["cafe", "park", "museum", "bar", "restaurant", "viewpoint"],
    default=["cafe", "park", "museum"],
)

if st.button("Build my day", use_container_width=True, type="primary"):
    with st.spinner("Building..."):
        try:
            it = api.itinerary(cats, city)
            st.session_state["itinerary"] = it
        except Exception as e:
            st.error(f"Couldn't build itinerary: {e}")

it = st.session_state.get("itinerary")
if it:
    st.success(f"~{it['total_minutes']} minutes total")

    # List the stops
    for i, stop in enumerate(it["stops"], start=1):
        st.markdown(f"""
        <div class="onepick-card">
          <h3>Stop {i}: {stop['name']}</h3>
          <div class="meta">{stop['address']} · {stop['category']}</div>
        </div>
        """, unsafe_allow_html=True)

    # Map all stops with a line between them
    if it["stops"]:
        first = it["stops"][0]
        m = folium.Map(location=[first["lat"], first["lon"]], zoom_start=14)
        coords = [[s["lat"], s["lon"]] for s in it["stops"]]
        for i, s in enumerate(it["stops"], start=1):
            folium.Marker(
                [s["lat"], s["lon"]],
                tooltip=f"{i}. {s['name']}",
                icon=folium.Icon(color="orange", icon="info-sign"),
            ).add_to(m)
        folium.PolyLine(coords, color="#FF6B47", weight=4, opacity=0.7).add_to(m)
        st_folium(m, height=400, use_container_width=True)
