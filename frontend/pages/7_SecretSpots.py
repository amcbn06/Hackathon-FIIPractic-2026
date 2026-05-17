import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import streamlit.components.v1 as components
from frontend import api_client as api

st.set_page_config(page_title="Secret Spots — South", page_icon="✨", layout="centered", initial_sidebar_state="expanded")

# Script pentru forțarea deschiderii meniului
components.html(
    """<script>
    const expandBtn = window.parent.document.querySelector('[data-testid="collapsedControl"]');
    if (expandBtn) expandBtn.click();
    </script>""", height=0, width=0
)

# Încărcare UI
img_path = Path(__file__).parent.parent / "images" / "logo.png"
if img_path.exists():
    st.logo(str(img_path), size="large")
css_path = Path(__file__).parent.parent / "style.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

# Meniul Customizat (Ai grijă să adaugi pagina asta și în meniurile din celelalte pagini, dacă vrei!)
with st.sidebar:
    if img_path.exists():
        st.logo(str(img_path), size="large")
    st.page_link("app.py", label="Home", icon="🏠")
    st.page_link("pages/3_Itinerary.py", label="Itinerary", icon="🗺️")
    st.page_link("pages/4_Friends.py", label="Friends", icon="👥")
    st.page_link("pages/5_Streak.py", label="Streak", icon="🔥")
    st.page_link("pages/6_History.py", label="Tracker", icon="✅")
    st.page_link("pages/7_SecretSpots.py", label="Secret Spots", icon="✨") # Pagina Nouă

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown('<div class="sidebar-brand-container"><span class="sidebar-brand-text">South</span></div>', unsafe_allow_html=True)
    st.markdown("<hr class='subtle'>", unsafe_allow_html=True)
    if st.button("Log out", use_container_width=True):
        api.clear_token()
        st.rerun()

if not api.is_logged_in():
    st.warning("Please log in from the main page.")
    st.stop()

st.markdown('<div class="page-title">My Secret Spots ✨</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Your personal journal of hidden gems and unmapped discoveries.</div>', unsafe_allow_html=True)
st.markdown("<hr class='subtle'>", unsafe_allow_html=True)

# 1. FORMULARUL
with st.expander("➕ Add a New Discovery", expanded=False):
    with st.form("custom_place_form", clear_on_submit=True):
        c_name = st.text_input("Location Name*", placeholder="e.g., Hidden Waterfall")
        c_desc = st.text_area("Description", placeholder="What makes it special?")
        
        col1, col2 = st.columns(2)
        with col1:
            c_int = st.text_input("Time Interval", placeholder="e.g., 2 hours / 10 AM - 6 PM")
        with col2:
            c_rating = st.slider("Rating (Stars)", min_value=1, max_value=5, value=5)
        
        submit_btn = st.form_submit_button("💾 Save to My Spots", type="primary", use_container_width=True)
        
        if submit_btn:
            if not c_name.strip():
                st.error("Please provide at least a name!")
            else:
                try:
                    api.add_custom_location(c_name, c_desc, c_int, c_rating)
                    st.success("Place added successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving place: {e}")

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("### My Personal Collection")

# 2. AFIȘAREA LOCAȚIILOR
try:
    my_spots = api.get_my_custom_locations()
    if not my_spots:
        st.info("You haven't added any custom spots yet. Be an explorer!")
    else:
        for spot in my_spots:
            st.markdown(f"""
            <div class="op-card" style="margin-bottom: 15px;">
              <div class="op-card-body">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h4 style="margin: 0;">📍 {spot['name']}</h4>
                    <span style="color: gold; font-size: 1.2rem;">{'★' * spot['rating']}{'☆' * (5 - spot['rating'])}</span>
                </div>
                <div style="font-size: 0.9rem; color: gray; margin-top: 5px;">
                    🕒 <b>Interval:</b> {spot['interval'] if spot['interval'] else 'N/A'} • 📅 Added on: {spot['created_at']}
                </div>
                <div style="margin-top: 10px; font-style: italic;">
                    "{spot['description']}"
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)
except Exception as e:
    st.error(f"Could not load your spots: {e}")