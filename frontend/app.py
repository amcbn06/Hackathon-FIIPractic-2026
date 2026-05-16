"""
Streamlit entry point — South with PlaceFind aesthetic.

Run:
    streamlit run frontend/app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from frontend import api_client as api

st.set_page_config(page_title="South", page_icon="", layout="centered")

img_path = Path(__file__).parent / "images" / "logo.png"
if img_path.exists():
    st.logo(str(img_path),size = "large")

# ─────────────────────────────

css_path = Path(__file__).parent / "style.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

css_path = Path(__file__).parent / "style.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


CATEGORIES = [
    ("cafe", "☕"), ("park", "🌳"), ("museum", "🏛️"),
    ("bar", "🍻"), ("restaurant", "🍽️"), ("viewpoint", "🌆"),
]


def _login_screen():
    st.markdown('<div class="login-title"> South</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-sub">Stop choosing. Start going.</div>', unsafe_allow_html=True)

    tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_pw")
            if st.form_submit_button("Log in", use_container_width=True):
                try:
                    api.login(email, password)
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")

    with tab_signup:
        with st.form("signup_form"):
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_pw")
            display_name = st.text_input("Display name", key="signup_name")
            if st.form_submit_button("Create account", use_container_width=True):
                try:
                    api.signup(email, password, display_name)
                    st.rerun()
                except Exception as e:
                    st.error(f"Signup failed: {e}")

    st.markdown(
        "<div class='login-demo-text'>Demo: <code>demo@South.app</code> / <code>demo1234</code></div>",
        unsafe_allow_html=True,
    )


def _home_screen():
    user = api.me()

    st.markdown(f'<div class="page-title">Hey, {user["display_name"]} 👋</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Pick a vibe. We pick the place.</div>', unsafe_allow_html=True)

    city = st.text_input("Where are you?", value="Iași", key="city")

    st.markdown('<div class="section-label">What are you in the mood for?</div>', unsafe_allow_html=True)

    cols = st.columns(3)
    for i, (cat, icon) in enumerate(CATEGORIES):
        with cols[i % 3]:
            if st.button(f"{icon} {cat.title()}", use_container_width=True, key=f"cat_{cat}"):
                with st.spinner("Finding the one..."):
                    result = api.pick(cat, city)
                st.session_state["last_pick"] = result
                st.switch_page("pages/2_Result.py")

    with st.sidebar:

        st.markdown(
            '<div class="sidebar-brand-container"><span class="sidebar-brand-text">South</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown(f'<div class="sidebar-email-text">{user["email"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sidebar-invite-text">Invite: <code>{user["invite_code"]}</code></div>', unsafe_allow_html=True)
        st.markdown("<hr class='subtle'>", unsafe_allow_html=True)
        if st.button("Log out", use_container_width=True):
            api.clear_token()
            st.rerun()


if not api.is_logged_in():
    _login_screen()
else:
    _home_screen()