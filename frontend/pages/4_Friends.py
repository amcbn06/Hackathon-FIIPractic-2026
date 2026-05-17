"""Friends + groups — all data from API."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from frontend import api_client as api

st.set_page_config(page_title="Social — OnePick", page_icon="🌍", layout="centered")


# --- Setup Logo & CSS ---
img_path = Path(__file__).parent.parent / "images" / "logo.png"
if img_path.exists():
    st.logo(str(img_path), size="large")
css_path = Path(__file__).parent.parent / "style.css"


if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

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

if not api.is_logged_in():
    st.warning("Please log in from the main page.")
    st.stop()
    
if "active_menu" not in st.session_state:
    st.session_state.active_menu = None
if "active_history" not in st.session_state:
    st.session_state.active_history = None
    
me = api.me()

st.markdown('<div class="page-title">Social Hub 🌍</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Manage your friends, requests, and groups.</div>', unsafe_allow_html=True)

# Aducem lista de prieteni global ca să o putem folosi și la grupuri
try:
    friend_list = api.friends()
    friend_map = {f["display_name"]: f["user_id"] for f in friend_list} if friend_list else {}
except Exception:
    friend_list = []
    friend_map = {}

# ==========================================
# 🎯 CREĂM TAB-URILE PENTRU ORGANIZARE
# ==========================================
tab_friends, tab_req, tab_groups = st.tabs(["👥 My Friends", "📨 Add & Requests", "🏘️ Groups"])

# ------------------------------------------
# TAB 1: LISTA DE PRIETENI ȘI OPȚIUNI
# ------------------------------------------
with tab_friends:
    st.markdown('<div class="section-label">Your connections</div>', unsafe_allow_html=True)
    if not friend_list:
        st.info("You haven't added any friends yet. Check the 'Add & Requests' tab!")
    else:
        for f in friend_list:
            fid = f['user_id']
            col_name, col_ops = st.columns([4, 1])
            
            with col_name:
                initials = "".join(w[0].upper() for w in f["display_name"].split()[:2])
                st.markdown(
                    f'<div class="friend-row" style="margin-bottom: 0px;">'
                    f'<div class="friend-row-inner">'
                    f'<div class="avatar">{initials}</div>'
                    f'<div class="friend-details">'
                    f'<div class="friend-name">{f["display_name"]}</div>'
                    f'<div class="friend-email">{f["email"]}</div>'
                    f'</div></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                
            with col_ops:
                st.write("") # aliniere
                if st.button("•••", key=f"ops_{fid}", help="More options"):
                    # Logica de acordeon:
                    if st.session_state.active_menu == fid:
                        # Dacă apăsăm pe același, îl închidem
                        st.session_state.active_menu = None 
                        st.session_state.active_history = None
                    else:
                        # Dacă apăsăm pe altul, devine el cel activ (se închid restul)
                        st.session_state.active_menu = fid 
                        st.session_state.active_history = None
                    st.rerun() # Reîncărcăm imediat interfața
            
            # Afișăm meniul ascuns DOAR dacă acest prieten este cel activ
            if st.session_state.active_menu == fid:
                with st.container():
                    st.markdown("---")
                    
                    if st.button("📜 View Location History", key=f"hist_{fid}", type="primary", use_container_width=True):
                        if st.session_state.active_history == fid:
                            st.session_state.active_history = None
                        else:
                            st.session_state.active_history = fid
                        st.rerun()
                    
                    col_rem, col_blk = st.columns(2)
                    with col_rem:
                        if st.button("❌ Remove Friend", key=f"rem_{fid}", use_container_width=True):
                            api.remove_friend(fid)
                            st.session_state.active_menu = None
                            st.session_state.active_history = None
                            st.rerun()
                    with col_blk:
                        if st.button("🚫 Block User", key=f"blk_{fid}", use_container_width=True):
                            api.block_friend(fid)
                            st.session_state.active_menu = None
                            st.session_state.active_history = None
                            st.rerun()
                    st.markdown("---")

            # Afișăm istoricul DOAR dacă e activat pentru acest prieten
            if st.session_state.active_history == fid:
                with st.expander(f"🕰️ {f['display_name']}'s Pick History", expanded=True):
                    history = api.get_friend_history(fid)
                    if not history:
                        st.text("No recent locations visited.")
                    else:
                        for idx, item in enumerate(history):
                            st.markdown(f"**{idx+1}. {item['place_name']}** — *{item['category']}*")
                            st.caption(f"📅 Recommended on: {item['created_at']}")
                    
                    if st.button("Close History", key=f"close_hist_{fid}"):
                        st.session_state.active_history = None
                        st.rerun()
            st.write("")
            
# ------------------------------------------
    # SECȚIUNEA BLOCKED USERS (Tot în Tab-ul 1)
    # ------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🚫 Blocked Users"):
        try:
            blocked = api.blocked_users()
            if not blocked:
                st.info("You haven't blocked anyone.")
            else:
                for b_user in blocked:
                    col_b_name, col_b_unblock = st.columns([3, 1])
                    with col_b_name:
                        st.markdown(f"**{b_user['display_name']}**<br><small>{b_user['email']}</small>", unsafe_allow_html=True)
                    with col_b_unblock:
                        if st.button("Unblock", key=f"unblk_{b_user['user_id']}", type="secondary"):
                            api.unblock_user(b_user['user_id'])
                            st.rerun()
        except Exception as e:
            st.error("Couldn't load blocked users.")
            
# ------------------------------------------
# TAB 2: INVITE CODE & FRIEND REQUESTS
# ------------------------------------------
with tab_req:
    # 1. Invite Code-ul tău
    st.markdown('<div class="section-label">Your invite code</div>', unsafe_allow_html=True)
    st.code(me["invite_code"], language=None)
    st.caption("Share this code with your friends so they can add you.")
    st.markdown("<hr class='subtle'>", unsafe_allow_html=True)

    # 2. Add Friend
    st.markdown('<div class="section-label">Add a new friend</div>', unsafe_allow_html=True)
    with st.form("add_friend"):
        code = st.text_input("Friend's invite code", placeholder="e.g. XYZ789").strip().upper()
        if st.form_submit_button("Send request", use_container_width=True):
            try:
                api.send_friend_request(code)
                st.success("Friend request sent!")
            except Exception as e:
                st.error(f"Couldn't send request: {e}")
                
    st.markdown("<hr class='subtle'>", unsafe_allow_html=True)

    # 3. Pending Requests
    st.markdown('<div class="section-label">Pending requests</div>', unsafe_allow_html=True)
    try:
        pending = api.pending_requests()
        if not pending:
            st.info("No pending requests at the moment.")
        else:
            for req in pending:
                col_name, col_accept, col_decline = st.columns([3, 1, 1])
                with col_name:
                    st.markdown(f"**{req['display_name']}**<br><small>{req['email']}</small>", unsafe_allow_html=True)
                with col_accept:
                    if st.button("Accept", key=f"acc_{req['user_id']}", type="primary"):
                        api.accept_friend_request(req["user_id"])
                        st.rerun()
                with col_decline:
                    if st.button("Decline", key=f"dec_{req['user_id']}"):
                        api.decline_friend_request(req["user_id"])
                        st.rerun()
    except Exception as e:
        st.error("Couldn't load requests.")

# ------------------------------------------
# TAB 3: GROUPS
# ------------------------------------------
with tab_groups:
    # --- SECȚIUNE NOUĂ: INVITAȚII PENDING PENTRU GRUPURI ---
    try:
        grp_invites = api.pending_group_invites()
        if grp_invites:
            st.markdown('<div class="section-label">📩 Group Invites</div>', unsafe_allow_html=True)
            for inv in grp_invites:
                ci1, ci2, ci3 = st.columns([3, 1, 1])
                with ci1:
                    st.write(f"**{inv['group_name']}**<br><small>Invited by {inv['sender_name']}</small>", unsafe_allow_html=True)
                with ci2:
                    if st.button("Accept", key=f"g_acc_{inv['invite_id']}", type="primary"):
                        api.accept_group_invite(inv['invite_id'])
                        st.rerun()
                with ci3:
                    if st.button("Decline", key=f"g_dec_{inv['invite_id']}"):
                        api.decline_group_invite(inv['invite_id'])
                        st.rerun()
            st.markdown("<hr class='subtle'>", unsafe_allow_html=True)
    except Exception as e:
        pass # Ignorăm eroarea dacă nu sunt invitații

    # --- CREARE GRUP ---
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

    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- LISTA GRUPURI ---
    try:
        groups = api.list_groups()
        if not groups:
            st.info("You are not part of any groups yet.")
        else:
            for g in groups:
                # Verificăm dacă utilizatorul curent este Adminul grupului
                is_admin = (g.get('owner_id') == me['id'])
                
                col_g1, col_g2 = st.columns([3, 1])
                with col_g1:
                    st.markdown(f"### {g['name']}")
                    if is_admin:
                        st.caption(f"👑 You are Admin • {len(g['member_ids'])} members")
                    else:
                        st.caption(f"{len(g['member_ids'])} members")
                with col_g2:
                    if is_admin:
                        # Buton de ștergere grup doar pentru Admin
                        if st.button("🗑️ Delete Group", key=f"del_g_{g['group_id']}", help="This action is permanent."):
                            api.delete_group(g['group_id'])
                            st.rerun()
            
                with st.expander("👥 View & Manage Members"):
                    existing_member_ids = []
                    
                    # 1. AFIȘAREA MEMBRILOR (Simplu și curat)
                    for m in g.get("members", []):
                        existing_member_ids.append(m["user_id"])
                        req_key = f"req_sent_{m['user_id']}"
                        
                        # Dacă ești tu
                        if m["user_id"] == me["id"]:
                            st.write(f"- 👤 **{m['display_name']}** (You)")
                        # Dacă e prieten
                        elif m["user_id"] in friend_map.values():
                            st.write(f"- 🤝 **{m['display_name']}** (Friend)")
                        # Dacă e trimisă deja cererea
                        elif st.session_state.get(req_key):
                            st.write(f"- ⏳ **{m['display_name']}** (Req sent)")
                        # Dacă e un străin (îi punem butonul de Add inline)
                        else:
                            col_m1, col_m2 = st.columns([3, 1])
                            with col_m1:
                                st.write(f"- 👤 **{m['display_name']}**")
                            with col_m2:
                                if st.button("➕ Add", key=f"add_m_{g['group_id']}_{m['user_id']}"):
                                    api.accept_invite(m['invite_code'])
                                    st.session_state[req_key] = True
                                    st.toast("Friend request sent!")
                                    st.rerun()
                    
                    st.markdown("---")
                    
                    # 2. ADMIN ZONE: SELECTBOX PENTRU KICK (Ce ai cerut tu!)
                    if is_admin and len(g.get("members", [])) > 1:
                        st.markdown("**👢 Kick a member:**")
                        kickable = {m["display_name"]: m["user_id"] for m in g.get("members", []) if m["user_id"] != me["id"]}
                        col_k1, col_k2 = st.columns([3, 1])
                        with col_k1:
                            user_to_kick = st.selectbox("Select user to kick", options=["-- Select --"] + list(kickable.keys()), key=f"sel_kick_{g['group_id']}", label_visibility="collapsed")
                        with col_k2:
                            if st.button("Kick", key=f"btn_kick_{g['group_id']}", type="secondary"):
                                if user_to_kick != "-- Select --":
                                    api.kick_group_member(g['group_id'], kickable[user_to_kick])
                                    st.toast(f"{user_to_kick} was kicked.")
                                    st.rerun()
                                else:
                                    st.warning("Select a user to kick.")
                        st.markdown("---")
                    
                    # 3. LOGICA PENTRU INVITAȚII NOI ÎN GRUP
                    invitable_friends = [f for f in friend_list if f["user_id"] not in existing_member_ids]
                    if invitable_friends:
                        st.markdown("**Invite more friends:**")
                        inv_opts = {f["display_name"]: f["user_id"] for f in invitable_friends}
                        col_sel, col_btn = st.columns([3, 1])
                        with col_sel:
                            sel_friend = st.selectbox("Select friend", options=["-- Select --"] + list(inv_opts.keys()), key=f"sel_inv_{g['group_id']}", label_visibility="collapsed")
                        with col_btn:
                            if st.button("Invite", key=f"btn_inv_{g['group_id']}"):
                                if sel_friend != "-- Select --":
                                    api.invite_to_group(g['group_id'], inv_opts[sel_friend])
                                    st.toast(f"Invite sent to {sel_friend}!")
                                else:
                                    st.warning("Please select a friend.")
                    else:
                        st.caption("All your friends are already in this group!")

                # Butonul de generare a locației pentru tot grupul
                cat = st.selectbox(
                    f"Category", 
                    ["cafe", "park", "museum", "bar", "restaurant", "viewpoint", "sport", "entertainment", "cultural"], 
                    key=f"gcat_{g['group_id']}"
                    )
                if st.button(f"🎯 Pick for {g['name']}", key=f"gpick_{g['group_id']}", type="primary"):
                    with st.spinner("Picking for the group..."):
                        p = api.group_pick(g["group_id"], cat, "Iași")
                    st.session_state["last_pick"] = p
                    st.switch_page("pages/2_Result.py")
                st.markdown("<hr class='subtle'>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Couldn't load groups: {e}")