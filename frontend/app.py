"""
Streamlit entry point.

Run:
    streamlit run frontend/app.py
"""

import sys
from pathlib import Path

# Make the project root importable when launched via `streamlit run`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from frontend import api_client as api

st.set_page_config(page_title="OnePick", page_icon="🎯", layout="centered")

# Inject custom CSS
css_path = Path(__file__).parent / "style.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


def _login_screen():
    st.title("🎯 OnePick")
    st.caption("Stop choosing. Start going.")

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
        "<br><br><center><small>"
        "Demo account: <code>demo@onepick.app</code> / <code>demo1234</code>"
        "</small></center>",
        unsafe_allow_html=True,
    )


def _home_screen():
    """Landing screen — category chips + Surprise Me button."""
    user = api.me()
    st.title(f"Hey, {user['display_name']} 👋")
    st.caption("Pick a vibe. We pick the place.")

    city = st.text_input("Where are you?", value="Iași", key="city")

    st.write("### What are you in the mood for?")
    cols = st.columns(3)
    categories = ["cafe", "park", "museum", "bar", "restaurant", "viewpoint"]
    icons = {"cafe": "☕", "park": "🌳", "museum": "🏛️",
             "bar": "🍻", "restaurant": "🍽️", "viewpoint": "🌆"}

    for i, cat in enumerate(categories):
        with cols[i % 3]:
            if st.button(f"{icons[cat]} {cat.title()}", use_container_width=True,
                         key=f"cat_{cat}"):
                with st.spinner("Finding the one..."):
                    result = api.pick(cat, city)
                st.session_state["last_pick"] = result
                st.switch_page("pages/2_Result.py")

    st.divider()
    with st.sidebar:
        st.write(f"**{user['email']}**")
        st.code(f"Invite code: {user['invite_code']}")
        if st.button("Log out"):
            api.clear_token()
            st.rerun()


# ----- Router ---------------------------------------------------------------

if not api.is_logged_in():
    _login_screen()
else:
    _home_screen()
