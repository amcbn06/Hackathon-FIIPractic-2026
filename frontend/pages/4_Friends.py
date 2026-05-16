"""Friends + groups — all data from API."""
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

st.markdown('<div class="page-title">Friends 👥</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Connect and pick places together.</div>', unsafe_allow_html=True)

# ── Invite code ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Your invite code</div>', unsafe_allow_html=True)
st.code(me["invite_code"], language=None)
st.caption("Share this with friends to connect.")

st.markdown("<hr class='subtle'>", unsafe_allow_html=True)

# ── Add friend ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Add a friend</div>', unsafe_allow_html=True)
with st.form("add_friend"):
    code = st.text_input("Friend's invite code", placeholder="e.g. XYZ789").strip().upper()
    if st.form_submit_button("Send request", use_container_width=True):
        try:
            api.send_friend_request(code)
            st.success("Friend request sent!")
        except Exception as e:
            st.error(f"Couldn't send request: {e}")

# ── Pending requests ─────────────────────────────────────────────────────────
try:
    pending = api.pending_requests()
    if pending:
        st.markdown("<hr class='subtle'>", unsafe_allow_html=True)
        st.markdown('<div class="section-label">Pending requests</div>', unsafe_allow_html=True)
        for req in pending:
            col_name, col_accept, col_decline = st.columns([3, 1, 1])
            with col_name:
                st.markdown(
                    f'<div class="friend-req-info">'
                    f'<strong>{req["display_name"]}</strong> · {req["email"]}</div>',
                    unsafe_allow_html=True,
                )
            with col_accept:
                if st.button("Accept", key=f"acc_{req['user_id']}"):
                    api.accept_friend_request(req["user_id"])
                    st.rerun()
            with col_decline:
                if st.button("Decline", key=f"dec_{req['user_id']}"):
                    api.decline_friend_request(req["user_id"])
                    st.rerun()
except Exception as e:
    st.error(f"Couldn't load pending requests: {e}")

st.markdown("<hr class='subtle'>", unsafe_allow_html=True)

# ── Friends list ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Your friends</div>', unsafe_allow_html=True)
try:
    friend_list = api.friends()
    if not friend_list:
        st.markdown('<div class="no-result">No friends yet — share your invite code.</div>', unsafe_allow_html=True)
    else:
        for f in friend_list:
            initials = "".join(w[0].upper() for w in f["display_name"].split()[:2])
            st.markdown(
                f'<div class="friend-row">'
                f'<div class="friend-row-inner">'
                f'<div class="avatar">{initials}</div>'
                f'<div class="friend-details">'
                f'<div class="friend-name">{f["display_name"]}</div>'
                f'<div class="friend-email">{f["email"]}</div>'
                f'</div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
except Exception as e:
    st.error(f"Couldn't load friends: {e}")

st.markdown("<hr class='subtle'>", unsafe_allow_html=True)

# ── Groups ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Groups</div>', unsafe_allow_html=True)

try:
    friend_list = api.friends()
    friend_map = {f["display_name"]: f["user_id"] for f in friend_list} if friend_list else {}

    with st.expander("➕ Create a new group"):
        with st.form("create_group"):
            name = st.text_input("Group name")
            if friend_map:
                picked = st.multiselect("Add friends", options=list(friend_map.keys()))
            else:
                st.caption("Add friends first to create a group with others.")
                picked = []
            if st.form_submit_button("Create group"):
                member_ids = [friend_map[n] for n in picked]
                api.create_group(name, member_ids)
                st.success("Group created!")
                st.rerun()

    CATEGORIES = ["cafe", "park", "museum", "bar", "restaurant", "viewpoint"]
    groups = api.list_groups()

    if not groups:
        st.markdown('<div class="no-groups-text">No groups yet.</div>', unsafe_allow_html=True)
    else:
        for g in groups:
            st.markdown(
                f'<div class="op-card"><div class="op-card-body">'
                f'<div class="group-title">{g["name"]}</div>'
                f'<div class="group-meta">{len(g["member_ids"])} me mbers</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
            col_cat, col_btn = st.columns([2, 1])
            with col_cat:
                cat = st.selectbox(
                    f"Category",
                    CATEGORIES,
                    key=f"gcat_{g['group_id']}",
                    label_visibility="collapsed",
                )
            with col_btn:
                if st.button(f"Pick →", key=f"gpick_{g['group_id']}", use_container_width=True):
                    with st.spinner("Picking for the group..."):
                        p = api.group_pick(g["group_id"], cat, "Iași")
                    st.session_state["last_pick"] = p
                    st.switch_page("pages/2_Result.py")

except Exception as e:
    st.error(f"Couldn't load groups: {e}")