"""The one card — the heart of the app."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import folium
from streamlit_folium import st_folium
from frontend import api_client as api

st.set_page_config(page_title="Your pick — South", page_icon="", layout="centered")
img_path = Path(__file__).parent.parent / "images" / "logo.png"
if img_path.exists():
    st.logo(str(img_path),size = "large")

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

# ── Place card ──────────────────────────────────────────────────────────────
st.markdown('<div class="op-card">', unsafe_allow_html=True)

if p.get("photo_url"):
    st.image(p["photo_url"], use_container_width=True)

st.markdown(f"""
<div class="op-card-body">
  <div class="op-card-title">{p['name']}</div>
  <div class="op-card-meta">{p.get('address', '')}</div>
  <div class="op-card-why">{p.get('why', '')}</div>
  <div class="op-card-meta">
    {'⭐ ' + str(p['rating']) + '&nbsp;&nbsp;' if p.get('rating') else ''}
    {'🕒 ' + p['hours'] if p.get('hours') else ''}
  </div>
</div>
""", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ── Map ─────────────────────────────────────────────────────────────────────
m = folium.Map(location=[p["lat"], p["lon"]], zoom_start=15, control_scale=True,
               tiles="CartoDB positron")
folium.Marker(
    [p["lat"], p["lon"]],
    tooltip=p["name"],
    icon=folium.Icon(color="darkblue", icon="map-marker", prefix="fa"), 
).add_to(m)
st_folium(m, height=300, use_container_width=True)

# ── Actions ─────────────────────────────────────────────────────────────────
st.markdown("<hr class='subtle'>", unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)

with c1:
    if st.button("🔁 Reroll", use_container_width=True):
        try:
            with st.spinner("Finding another..."):
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
    t1, t2 = st.columns(2)
    with t1:
        if st.button("👍", use_container_width=True):
            api.thumbs(p["pick_id"], 1)
            st.toast("Thanks!")
    with t2:
        if st.button("👎", use_container_width=True):
            api.thumbs(p["pick_id"], -1)
            st.toast("Noted.")

with st.sidebar:

    # 1. Your Logo
    img_path = Path(__file__).parent / "images" / "logo.png"
    if img_path.exists():
        st.logo(str(img_path), size="large")

    # 2. Your Custom Navigation Menu
    # (This replaces the ugly default menu we hid with CSS)
    st.page_link("app.py", label="Home", icon="🏠")
    st.page_link("pages/3_Itinerary.py", label="Itinerary", icon="🗺️")
    st.page_link("pages/4_Friends.py", label="Friends", icon="👥")
    st.page_link("pages/5_Streak.py", label="Streak", icon="🔥")
    st.page_link("pages/6_History.py", label="History", icon="📜")
    st.page_link("pages/7_SecretSpots.py", label="Recomandations", icon="✨")

    # Adding a little vertical space before the profile section
    st.markdown("<br><br>", unsafe_allow_html=True)

    # 3. User Profile & Logout
    st.markdown(
        '<div class="sidebar-brand-container"><span class="sidebar-brand-text">South</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown("<hr class='subtle'>", unsafe_allow_html=True)
    if st.button("Log out", use_container_width=True):
        api.clear_token()
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)
if st.button("← Pick something else"):
    st.switch_page("pages/1_Home.py")

