"""Past picks."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from frontend import api_client as api

st.set_page_config(page_title="History — OnePick", page_icon="📜", layout="centered")

css = (Path(__file__).parent.parent / "style.css").read_text()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

if not api.is_logged_in():
    st.warning("Please log in from the main page.")
    st.stop()

st.title("Your picks 📜")

try:
    data = api.history()
    picks = data.get("picks", [])
    if not picks:
        st.caption("No picks yet — head to Home and tap a category.")

    for p in picks:
        check = "✅" if p["visited"] else "⬜"
        st.markdown(f"""
        <div class="onepick-card">
          <h3>{check} {p['place_name']}</h3>
          <div class="meta">{p['category']} · {p['city']} · {(p.get('created_at') or '')[:10]}</div>
          <div class="why">{p['why']}</div>
        </div>
        """, unsafe_allow_html=True)
except Exception as e:
    st.error(f"Couldn't load history: {e}")
