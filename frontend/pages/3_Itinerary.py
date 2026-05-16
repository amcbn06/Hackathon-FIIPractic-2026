"""Day itinerary — multiple stops in order."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import folium
from streamlit_folium import st_folium
from frontend import api_client as api

st.set_page_config(page_title="Itinerary — OnePick", page_icon="🗺️", layout="centered")
img_path = Path(__file__).parent.parent / "images" / "logo.png"
if img_path.exists():
    st.logo(str(img_path),size = "large")
css = (Path(__file__).parent.parent / "style.css").read_text()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

if not api.is_logged_in():
    st.warning("Please log in from the main page.")
    st.stop()

st.markdown('<div class="page-title">Build a day 🗺️</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Tell us a few moods. We\'ll route them in order.</div>', unsafe_allow_html=True)

CATEGORIES = ["cafe", "park", "museum", "bar", "restaurant", "viewpoint"]

city = st.text_input("City", value="Iași")
cats = st.multiselect(
    "What's your day like?",
    options=CATEGORIES,
    default=["cafe", "park", "museum"],
    label_visibility="visible",
)

if st.button("Build my day", use_container_width=True, type="primary"):
    with st.spinner("Building your itinerary..."):
        try:
            it = api.itinerary(cats, city)
            st.session_state["itinerary"] = it
        except Exception as e:
            st.error(f"Couldn't build itinerary: {e}")

it = st.session_state.get("itinerary")
if it:
    st.markdown("<hr class='subtle'>", unsafe_allow_html=True)
    st.markdown(
        f'<div class="itinerary-total-time">🕒 About <strong>{it["total_minutes"]} minutes</strong> total</div>',
        unsafe_allow_html=True,
    )

    for i, stop in enumerate(it["stops"], start=1):
        st.markdown(f"""
        <div class="op-card">
          <div class="op-card-body">
            <div class="itinerary-stop-label">
              Stop {i}
            </div>
            <div class="op-card-title stop-title">{stop['name']}</div>
            <div class="op-card-meta">{stop['address']} · <span class="op-tag">{stop['category']}</span></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    if it["stops"]:
        first = it["stops"][0]
        m = folium.Map(location=[first["lat"], first["lon"]], zoom_start=14,
                       tiles="CartoDB positron")
        for i, s in enumerate(it["stops"], start=1):
            folium.Marker(
                [s["lat"], s["lon"]],
                tooltip=f"{i}. {s['name']}",
                icon=folium.Icon(color="darkblue", icon="circle", prefix="fa"),
            ).add_to(m)
        coords = [[s["lat"], s["lon"]] for s in it["stops"]]
        folium.PolyLine(coords, color="#F8F9FA", weight=2.5, opacity=0.8, dash_array="6").add_to(m)
        st_folium(m, height=380, use_container_width=True)