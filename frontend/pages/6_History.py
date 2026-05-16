"""Past picks — all data from API."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from frontend import api_client as api

st.set_page_config(page_title="History — OnePick", page_icon="📜", layout="centered")
img_path = Path(__file__).parent.parent / "images" / "logo.png"
if img_path.exists():
    st.logo(str(img_path),size = "large")
css = (Path(__file__).parent.parent / "style.css").read_text()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

if not api.is_logged_in():
    st.warning("Please log in from the main page.")
    st.stop()

st.markdown('<div class="page-title">Your picks 📜</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Every place you\'ve explored.</div>', unsafe_allow_html=True)

try:
    data = api.history()
    picks = data.get("picks", [])

    if not picks:
        st.markdown(
            '<div class="no-result">No picks yet.<br>Head to Home and tap a category.</div>',
            unsafe_allow_html=True,
        )
    else:
        # Filter controls
        col_filter, col_sort = st.columns(2)
        with col_filter:
            show_filter = st.selectbox(
                "Show",
                ["All", "Visited", "Not visited"],
                label_visibility="collapsed",
            )
        with col_sort:
            sort_order = st.selectbox(
                "Sort",
                ["Newest first", "Oldest first"],
                label_visibility="collapsed",
            )

        # Apply filter
        if show_filter == "Visited":
            picks = [p for p in picks if p["visited"]]
        elif show_filter == "Not visited":
            picks = [p for p in picks if not p["visited"]]

        # Apply sort
        if sort_order == "Oldest first":
            picks = list(reversed(picks))

        st.markdown("<hr class='subtle'>", unsafe_allow_html=True)
        st.markdown(
            f'<div class="section-label">{len(picks)} pick{"s" if len(picks) != 1 else ""}</div>',
            unsafe_allow_html=True,
        )

        for p in picks:
            check = "✅" if p["visited"] else "⬜"
            date_str = p["created_at"][:10] if p.get("created_at") else ""
            st.markdown(f"""
            <div class="op-card">
              <div class="op-card-body">
                <div class="op-card-title history-title">{check} {p['place_name']}</div>
                <div class="op-card-meta history-meta">
                  <span class="op-tag">{p['category']}</span>
                  &nbsp;{p['city']}&nbsp;·&nbsp;{date_str}
                </div>
                <div class="op-card-why">{p['why']}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Couldn't load history: {e}")