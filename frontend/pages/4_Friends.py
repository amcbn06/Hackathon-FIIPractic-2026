"""Friends + groups."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from frontend import api_client as api

st.set_page_config(page_title="Friends — OnePick", page_icon="👥", layout="centered")

css = (Path(__file__).parent.parent / "style.css").read_text()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

if not api.is_logged_in():
    st.warning("Please log in from the main page.")
    st.stop()

me = api.me()

st.title("Friends 👥")

st.write("### Your invite code")
st.code(me["invite_code"], language=None)
st.caption("Share this with a friend to connect.")

st.divider()

st.write("### Add a friend")
with st.form("add_friend"):
    code = st.text_input("Friend's invite code").strip().upper()
    if st.form_submit_button("Add"):
        try:
            f = api.accept_invite(code)
            st.success(f"Connected with {f['display_name']} ({f['email']})")
        except Exception as e:
            st.error(f"Couldn't add: {e}")

st.divider()
st.write("### Your friends")
try:
    friends = api.friends()
    if not friends:
        st.caption("No friends yet — share your invite code.")
    for f in friends:
        st.markdown(f"- **{f['display_name']}** · {f['email']}")
except Exception as e:
    st.error(f"Couldn't load friends: {e}")

st.divider()
st.write("### Groups")
try:
    friends = friends or []
    friend_map = {f["display_name"]: f["user_id"] for f in friends}

    with st.expander("➕ Create a new group"):
        with st.form("create_group"):
            name = st.text_input("Group name")
            picked = st.multiselect("Add friends", options=list(friend_map.keys()))
            if st.form_submit_button("Create group"):
                member_ids = [friend_map[n] for n in picked]
                api.create_group(name, member_ids)
                st.success("Group created.")
                st.rerun()

    groups = api.list_groups()
    if not groups:
        st.caption("No groups yet.")
    for g in groups:
        st.markdown(f"**{g['name']}** — {len(g['member_ids'])} members")
        cat = st.selectbox(f"Category for {g['name']}",
                           ["cafe", "park", "museum", "bar", "restaurant", "viewpoint"],
                           key=f"gcat_{g['group_id']}")
        if st.button(f"Pick for {g['name']}", key=f"gpick_{g['group_id']}"):
            with st.spinner("Picking for the group..."):
                p = api.group_pick(g["group_id"], cat, "Iași")
            st.session_state["last_pick"] = p
            st.switch_page("pages/2_Result.py")
except Exception as e:
    st.error(f"Couldn't load groups: {e}")
