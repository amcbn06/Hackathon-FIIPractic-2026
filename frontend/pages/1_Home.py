"""Home — duplicate of app.py home so the sidebar nav shows it."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from frontend import api_client as api

st.set_page_config(page_title="Home — OnePick", page_icon="🎯", layout="centered")

css = (Path(__file__).parent.parent / "style.css").read_text()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

if not api.is_logged_in():
    st.warning("Please log in from the main page.")
    st.stop()

user = api.me()
st.title(f"Hey, {user['display_name']} 👋")
st.caption("Pick a vibe. We pick the place.")

city = st.text_input("Where are you?", value="Iași")

st.write("### What are you in the mood for?")
cols = st.columns(3)
categories = [("cafe", "☕"), ("park", "🌳"), ("museum", "🏛️"),
              ("bar", "🍻"), ("restaurant", "🍽️"), ("viewpoint", "🌆")]

for i, (cat, icon) in enumerate(categories):
    with cols[i % 3]:
        if st.button(f"{icon} {cat.title()}", use_container_width=True, key=f"h_{cat}"):
            with st.spinner("Finding the one..."):
                st.session_state["last_pick"] = api.pick(cat, city)
            st.switch_page("pages/2_Result.py")
