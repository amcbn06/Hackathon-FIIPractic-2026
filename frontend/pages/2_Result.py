"""The one card — the heart of the app."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import folium
from streamlit_folium import st_folium

from frontend import api_client as api

st.set_page_config(page_title="Your pick — OnePick", page_icon="🎯", layout="centered")

css = (Path(__file__).parent.parent / "style.css").read_text()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

if not api.is_logged_in():
    st.warning("Please log in from the main page.")
    st.stop()

p = st.session_state.get("last_pick")
if not p:
    st.info("No pick yet — head back to Home and pick a category.")
    if st.button("← Home"):
        st.switch_page("pages/1_Home.py")
    st.stop()


st.markdown(f"""
<div class="onepick-card">
  <h2>{p['name']}</h2>
  <div class="meta">{p.get('address','')}</div>
  <div class="why">{p.get('why','')}</div>
  <div class="meta">
    {'⭐ ' + str(p['rating']) + '   ' if p.get('rating') else ''}
    {'🕒 ' + p['hours'] if p.get('hours') else ''}
  </div>
</div>
""", unsafe_allow_html=True)

# Map widget
m = folium.Map(location=[p["lat"], p["lon"]], zoom_start=15, control_scale=True)
folium.Marker([p["lat"], p["lon"]], tooltip=p["name"]).add_to(m)
st_folium(m, height=320, use_container_width=True)


c1, c2, c3 = st.columns(3)
with c1:
    if st.button("🔁 Reroll", use_container_width=True):
        try:
            with st.spinner("Re-rolling..."):
                st.session_state["last_pick"] = api.reroll(p["pick_id"])
            st.rerun()
        except Exception as e:
            st.error(f"Couldn't reroll: {e}")

with c2:
    if st.button("✅ I went!", use_container_width=True):
        try:
            res = api.mark_visited(p["pick_id"])
            st.success(f"Streak: {res['streak_current']} 🔥")
        except Exception as e:
            st.error(f"Failed: {e}")

with c3:
    thumb_col_a, thumb_col_b = st.columns(2)
    with thumb_col_a:
        if st.button("👍", use_container_width=True):
            api.thumbs(p["pick_id"], 1)
            st.toast("Thanks for the signal!")
    with thumb_col_b:
        if st.button("👎", use_container_width=True):
            api.thumbs(p["pick_id"], -1)
            st.toast("Noted.")

st.divider()
if st.button("← Pick something else"):
    st.switch_page("pages/1_Home.py")
