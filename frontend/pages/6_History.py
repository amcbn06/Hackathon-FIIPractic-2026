import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from frontend import api_client as api

# 1. Configurația paginii exact ca la celelalte
st.set_page_config(page_title="History — South", page_icon="📜", layout="centered", initial_sidebar_state="expanded")

# 2. Încărcare LOGO și CSS (Magia vizuală)
img_path = Path(__file__).parent.parent / "images" / "logo.png"
if img_path.exists():
    st.logo(str(img_path), size="large")

css_path = Path(__file__).parent.parent / "style.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

# 3. VERIFICARE LOGARE
if not api.is_logged_in():
    st.warning("Please log in from the main page.")
    st.stop()

# ==============================================================================
# ⚠️ NOTĂ IMPORTANTĂ PENTRU JURIU / HACKATHON:
# Dacă în celelalte pagini (cum ar fi 4_Friends.py) ai sus o linie de tipul:
# ui.render_sidebar() sau sidebar.render() sau ceva asemănător importat,
# adaug-o exact aici sub această linie! Ea va desena meniul vostru custom.
# ==============================================================================

# 4. DESIGN TITLU (Să se pupe cu fișierul style.css)
st.markdown('<div class="page-title">History 📜</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Manage your To-Do list and see where you\'ve been.</div>', unsafe_allow_html=True)
st.markdown("<hr class='subtle'>", unsafe_allow_html=True)

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
    st.page_link("pages/7_SecretSpots.py", label="Secret Spots", icon="✨")

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
        
# 5. PRELUARE DATE DIN BACKEND
try:
    data = api.advanced_history()
    todo = data["todo"]
    history = data["history"]
except Exception as e:
    st.error(f"Eroare la încărcarea datelor: {e}")
    st.stop()

# 6. MODULUL SUPREM: TO DO vs HISTORY
tab_todo, tab_hist = st.tabs(["📝 To Do (Pending)", "🏆 History (Visited)"])

# ==========================================
# MODULE 1: TO DO
# ==========================================
with tab_todo:
    sub_solo, sub_group, sub_itin = st.tabs(["👤 Solo Picks", "👥 Group Picks", "🗺️ Itineraries"])
    
    with sub_solo:
        if not todo["solo"]:
            st.info("You don't have any pending solo places. Go pick one!")
        for item in todo["solo"]:
            col1, col2 = st.columns([3, 1])
            col1.markdown(f"**{item['place_name']}** • *{item['category']}*")
            if col2.button("📍 Check-in", key=f"todo_solo_{item['pick_id']}", type="primary"):
                api.mark_visited(item['pick_id'])
                st.toast(f"Checked in at {item['place_name']}!")
                st.rerun()
            st.markdown("---")

    with sub_group:
        if not todo["group"]:
            st.info("No pending group places.")
        for item in todo["group"]:
            st.markdown(f"**{item['place_name']}** • *{item['group_name']}*")
            
            # Bara de progres pentru grup (Aici rupi juriul!)
            progress = item['checked_in_count'] / item['total_members']
            st.progress(progress, text=f"{item['checked_in_count']} / {item['total_members']} members checked in")
            
            if item['i_checked_in']:
                st.success("✅ You checked in! Waiting for the others...")
            else:
                if st.button("📍 Check-in", key=f"todo_grp_{item['pick_id']}", type="primary"):
                    api.mark_visited(item['pick_id'])
                    st.toast("Check-in registered!")
                    st.rerun()
            st.markdown("---")
            
    with sub_itin:
        if not todo.get("itineraries"):
            st.info("No pending itineraries. Generate one from the Itinerary tab!")
        for itin in todo.get("itineraries", []):
            st.markdown(f"### 🗺️ Itinerary in {itin['city']} <small>({itin['created_at']})</small>", unsafe_allow_html=True)
            
            # Bară de progres pentru traseu
            progress = itin['visited_stops'] / itin['total_stops'] if itin['total_stops'] > 0 else 0
            st.progress(progress, text=f"{itin['visited_stops']} / {itin['total_stops']} stops visited")
            
            # Afișăm fiecare oprire
            for stop in itin['stops']:
                c_name, c_btn = st.columns([3, 1])
                if stop['visited']:
                    c_name.markdown(f"✅ ~~{stop['place_name']}~~ *(Visited)*")
                else:
                    c_name.markdown(f"📍 **{stop['place_name']}** • *{stop['category']}*")
                    if c_btn.button("Check-in", key=f"btn_stop_{stop['stop_id']}", type="secondary"):
                        api.mark_itinerary_stop(stop['stop_id'])
                        st.rerun()
            st.markdown("---")
# ==========================================
# MODULE 2: HISTORY
# ==========================================
with tab_hist:
    hist_solo, hist_group, hist_itin = st.tabs(["👤 Solo Picks", "👥 Group Picks", "🗺️ Itineraries"])
    
    with hist_solo:
        if not history["solo"]:
            st.info("No visited places yet.")
        for item in history["solo"]:
            st.markdown(f"✅ **{item['place_name']}** • *{item['category']}*")
            st.markdown("---")

    with hist_group:
        if not history["group"]:
            st.info("No completed group visits yet.")
        for item in history["group"]:
            st.markdown(f"🏆 **{item['place_name']}** • *{item['group_name']}*")
            st.caption("All members checked in successfully!")
            st.markdown("---")
            
    with hist_itin:
        if not history.get("itineraries"):
            st.info("No completed itineraries yet.")
        for itin in history.get("itineraries", []):
            st.markdown(f"🏆 **Completed Itinerary in {itin['city']}**")
            st.caption(f"All {itin['total_stops']} stops visited! Created on: {itin['created_at']}")
            for stop in itin['stops']:
                st.markdown(f"✅ {stop['place_name']} • *{stop['category']}*")
            st.markdown("---")