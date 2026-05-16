"""Home page — category picker."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from frontend import api_client as api

st.set_page_config(page_title="Home — OnePick", page_icon="🎯", layout="centered")

css = (Path(__file__).parent.parent / "style.css").read_text()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

img_path = Path(__file__).parent / "images" / "logo.png"
if img_path.exists():
    st.logo(str(img_path),size = "large")
if not api.is_logged_in():
    st.warning("Please log in from the main page.")
    st.stop()

user = api.me()

st.markdown(f'<div class="page-title">Hey, {user["display_name"]} 👋</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Pick a vibe. We pick the place.</div>', unsafe_allow_html=True)

city = st.text_input("Where are you?", value="Iași", key="city")

st.markdown('<div class="section-label">What are you in the mood for?</div>', unsafe_allow_html=True)

CATEGORIES = [
    ("cafe", "☕"), ("park", "🌳"), ("museum", "🏛️"),
    ("bar", "🍻"), ("restaurant", "🍽️"), ("viewpoint", "🌆"),
]

cols = st.columns(3)
for i, (cat, icon) in enumerate(CATEGORIES):
    with cols[i % 3]:
        if st.button(f"{icon} {cat.title()}", use_container_width=True, key=f"h_{cat}"):
            with st.spinner("Finding the one..."):
                st.session_state["last_pick"] = api.pick(cat, city)
            st.switch_page("pages/2_Result.py")