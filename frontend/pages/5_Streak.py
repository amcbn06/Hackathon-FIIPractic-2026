"""Streak page."""
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

st.markdown('<div class="page-title">Your streak 🔥</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Visit one new place per day to keep it alive.</div>', unsafe_allow_html=True)

try:
    s = api.streak()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="streak-flame">🔥</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="streak-number">{s["current"]}</div>', unsafe_allow_html=True)
    st.markdown('<div class="streak-label">day streak</div>', unsafe_allow_html=True)

    st.markdown("<hr class='subtle'>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    c1.metric("Longest streak", f"{s['longest']} days")
    c2.metric("Last visit", s.get("last_visit_date") or "—")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div class="streak-warning">Miss a day and your streak resets to zero. Keep exploring!</div>',
        unsafe_allow_html=True,
    )

except Exception as e:
    st.error(f"Couldn't load streak: {e}")