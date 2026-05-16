"""Streak flame."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from frontend import api_client as api

st.set_page_config(page_title="Streak — OnePick", page_icon="🔥", layout="centered")

css = (Path(__file__).parent.parent / "style.css").read_text()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

if not api.is_logged_in():
    st.warning("Please log in from the main page.")
    st.stop()

st.title("Your streak 🔥")

try:
    s = api.streak()
    st.markdown(f"<div class='streak-flame'>🔥</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='streak-number'>{s['current']}</div>",
                unsafe_allow_html=True)
    st.markdown(f"<center>day streak</center>", unsafe_allow_html=True)

    st.divider()
    c1, c2 = st.columns(2)
    c1.metric("Longest streak", f"{s['longest']} days")
    c2.metric("Last visit", s.get("last_visit_date") or "—")

    st.caption(
        "Visit one new place per day to keep your streak. Miss a day and it resets."
    )
except Exception as e:
    st.error(f"Couldn't load streak: {e}")
