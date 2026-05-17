"""
Thin HTTP client that every Streamlit page imports.
"""

import os
from typing import Dict, List, Optional

import requests
import streamlit as st

from dotenv import load_dotenv
load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"


# ----- Session token helpers ------------------------------------------------

def set_token(token: str, user_id: int) -> None:
    st.session_state["token"] = token
    st.session_state["user_id"] = user_id

def get_token() -> Optional[str]:
    return st.session_state.get("token")

def clear_token() -> None:
    st.session_state.pop("token", None)
    st.session_state.pop("user_id", None)

def is_logged_in() -> bool:
    return get_token() is not None

def _headers() -> Dict[str, str]:
    tok = get_token()
    return {"Authorization": f"Bearer {tok}"} if tok else {}

def _raise(r: requests.Response) -> None:
    if not r.ok:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        st.error(f"Error {r.status_code}: {detail}")
        st.stop()


# ----- Real HTTP wrappers (with mock fallback) ------------------------------

def signup(email: str, password: str, display_name: str = "") -> Dict:
    if MOCK_MODE:
        set_token("mock-token", 1)
        return {"token": "mock-token", "user_id": 1}
    r = requests.post(f"{BACKEND_URL}/signup", json={
        "email": email, "password": password, "display_name": display_name,
    }, timeout=10)
    _raise(r)
    data = r.json()
    set_token(data["token"], data["user_id"])
    return data

def login(email: str, password: str) -> Dict:
    if MOCK_MODE:
        set_token("mock-token", 1)
        return {"token": "mock-token", "user_id": 1}
    r = requests.post(f"{BACKEND_URL}/login", json={
        "email": email, "password": password,
    }, timeout=10)
    _raise(r)
    data = r.json()
    set_token(data["token"], data["user_id"])
    return data

def me() -> Dict:
    if MOCK_MODE:
        return {"id": 1, "email": "demo@onepick.app",
                "display_name": "Demo", "invite_code": "ABC123"}
    r = requests.get(f"{BACKEND_URL}/me", headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def pick(category: str, city: str, group_id: Optional[int] = None) -> Dict:
    if MOCK_MODE:
        return {
            "pick_id": 42,
            "place_id": "mock-1",
            "name": f"Mock {category.title()} on Lăpușneanu",
            "address": "Strada Lăpușneanu 14, Iași",
            "lat": 47.1700, "lon": 27.5780,
            "why": f"Top-rated {category} you haven't visited this week.",
            "rating": 4.5, "photo_url": None, "hours": "08:00-22:00",
        }
    r = requests.post(f"{BACKEND_URL}/pick",
                      json={"category": category, "city": city, "group_id": group_id},
                      headers=_headers(), timeout=15)
    _raise(r)
    return r.json()

def reroll(pick_id: int) -> Dict:
    if MOCK_MODE:
        return pick("cafe", "Iași")
    r = requests.post(f"{BACKEND_URL}/pick/{pick_id}/reroll",
                      headers=_headers(), timeout=15)
    _raise(r)
    return r.json()

def mark_visited(pick_id: int) -> Dict:
    if MOCK_MODE:
        return {"streak_current": 8, "streak_longest": 12}
    r = requests.post(f"{BACKEND_URL}/pick/{pick_id}/visited",
                      headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def thumbs(pick_id: int, value: int) -> Dict:
    if MOCK_MODE:
        return {"thumbs": value}
    r = requests.post(f"{BACKEND_URL}/pick/{pick_id}/thumbs",
                      params={"value": value},
                      headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def itinerary(categories: List[str], city: str, day: Optional[str] = None) -> Dict:
    if MOCK_MODE:
        return {
            "stops": [
                {"place_id": "m1", "name": "Mock Café",  "address": "...", "lat": 47.170, "lon": 27.578, "category": "cafe"},
                {"place_id": "m2", "name": "Mock Park",  "address": "...", "lat": 47.185, "lon": 27.573, "category": "park"},
                {"place_id": "m3", "name": "Mock Museum","address": "...", "lat": 47.157, "lon": 27.588, "category": "museum"},
            ],
            "total_minutes": 110,
        }
    r = requests.post(f"{BACKEND_URL}/itinerary",
                      json={"categories": categories, "city": city, "day": day},
                      headers=_headers(), timeout=20)
    _raise(r)
    return r.json()

def friends() -> List[Dict]:
    if MOCK_MODE:
        return [{"user_id": 2, "display_name": "Ana", "email": "ana@onepick.app"}]
    r = requests.get(f"{BACKEND_URL}/friends", headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def send_friend_request(invite_code: str) -> Dict:
    if MOCK_MODE:
        return {"detail": "Friend request sent"}
    r = requests.post(f"{BACKEND_URL}/friends/request",
                      json={"invite_code": invite_code},
                      headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def accept_friend_request(requester_id: int) -> Dict:
    if MOCK_MODE:
        return {"user_id": requester_id, "display_name": "Ana", "email": "ana@onepick.app"}
    r = requests.post(f"{BACKEND_URL}/friends/accept",
                      params={"requester_id": requester_id},
                      headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def accept_invite(invite_code: str) -> Dict:
    r = requests.post(f"{BACKEND_URL}/friends/request",
                      json={"invite_code": invite_code},
                      headers=_headers(), timeout=10)
    if r.status_code == 400:
        return {"detail": "Request already sent"}
    _raise(r)
    return r.json()

def decline_friend_request(requester_id: int) -> Dict:
    if MOCK_MODE:
        return {"detail": "Request declined"}
    r = requests.post(f"{BACKEND_URL}/friends/decline",
                      params={"requester_id": requester_id},
                      headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def pending_requests() -> List[Dict]:
    if MOCK_MODE:
        return [{"user_id": 3, "display_name": "Mihai", "email": "mihai@onepick.app"}]
    r = requests.get(f"{BACKEND_URL}/friends/pending",
                     headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def create_group(name: str, member_ids: List[int]) -> Dict:
    if MOCK_MODE:
        return {"group_id": 1, "name": name, "member_ids": [1] + member_ids}
    r = requests.post(f"{BACKEND_URL}/groups",
                      json={"name": name, "member_ids": member_ids},
                      headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def list_groups() -> List[Dict]:
    if MOCK_MODE:
        return [{"group_id": 1, "name": "Weekend Crew", "member_ids": [1, 2]}]
    r = requests.get(f"{BACKEND_URL}/groups", headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def group_pick(group_id: int, category: str, city: str) -> Dict:
    if MOCK_MODE:
        return pick(category, city, group_id=group_id)
    r = requests.post(f"{BACKEND_URL}/groups/{group_id}/pick",
                      json={"category": category, "city": city},
                      headers=_headers(), timeout=15)
    _raise(r)
    return r.json()

def streak() -> Dict:
    if MOCK_MODE:
        return {"current": 7, "longest": 12, "last_visit_date": "2026-05-15"}
    r = requests.get(f"{BACKEND_URL}/me/streak", headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def history(limit: int = 50) -> Dict:
    if MOCK_MODE:
        return {"picks": []}
    r = requests.get(f"{BACKEND_URL}/me/history",
                     headers=_headers(), params={"limit": limit}, timeout=10)
    _raise(r)
    return r.json()

def list_places(category: Optional[str] = None, city: Optional[str] = None, status: Optional[str] = None) -> List[Dict]:
    if MOCK_MODE: return []
    params = {k: v for k, v in {"category": category, "city": city, "status": status}.items() if v}
    r = requests.get(f"{BACKEND_URL}/places", headers=_headers(), params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def list_pending_places(city: Optional[str] = None) -> List[Dict]:
    if MOCK_MODE: return []
    params = {"city": city} if city else {}
    r = requests.get(f"{BACKEND_URL}/places/pending", headers=_headers(), params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def suggest_place(payload: Dict) -> Dict:
    if MOCK_MODE: return {**payload, "id": 999, "status": "pending", "vote_count": 0}
    r = requests.post(f"{BACKEND_URL}/places/suggest", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()

def vote_place(place_id: int) -> Dict:
    if MOCK_MODE: return {"id": place_id, "vote_count": 1, "status": "pending"}
    r = requests.post(f"{BACKEND_URL}/places/{place_id}/vote", headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()

def admin_approve_place(place_id: int) -> Dict:
    if MOCK_MODE: return {"id": place_id, "status": "approved"}
    r = requests.post(f"{BACKEND_URL}/places/{place_id}/approve", headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()

def admin_reject_place(place_id: int) -> Dict:
    if MOCK_MODE: return {"id": place_id, "status": "rejected"}
    r = requests.post(f"{BACKEND_URL}/places/{place_id}/reject", headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()

def admin_delete_place(place_id: int) -> Dict:
    if MOCK_MODE: return {"deleted": place_id}
    r = requests.delete(f"{BACKEND_URL}/places/{place_id}", headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()

def get_friend_history(friend_id: int) -> List[Dict]:
    if MOCK_MODE: return []
    r = requests.get(f"{BACKEND_URL}/friends/{friend_id}/history", headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def remove_friend(friend_id: int) -> Dict:
    if MOCK_MODE: return {"detail": "Friend removed successfully"}
    r = requests.delete(f"{BACKEND_URL}/friends/{friend_id}", headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def block_friend(friend_id: int) -> Dict:
    if MOCK_MODE: return {"detail": "User blocked successfully"}
    r = requests.post(f"{BACKEND_URL}/friends/{friend_id}/block", headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def blocked_users() -> List[Dict]:
    if MOCK_MODE: return []
    r = requests.get(f"{BACKEND_URL}/friends/blocked", headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def unblock_user(friend_id: int) -> Dict:
    if MOCK_MODE: return {"detail": "User unblocked successfully"}
    r = requests.post(f"{BACKEND_URL}/friends/{friend_id}/unblock", headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def invite_to_group(group_id: int, user_id: int) -> Dict:
    if MOCK_MODE: return {}
    r = requests.post(f"{BACKEND_URL}/groups/{group_id}/invite", params={"user_id": user_id}, headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def pending_group_invites() -> List[Dict]:
    if MOCK_MODE: return []
    r = requests.get(f"{BACKEND_URL}/groups/invites/pending", headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def accept_group_invite(invite_id: int) -> Dict:
    if MOCK_MODE: return {}
    r = requests.post(f"{BACKEND_URL}/groups/invites/{invite_id}/accept", headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def decline_group_invite(invite_id: int) -> Dict:
    if MOCK_MODE: return {}
    r = requests.post(f"{BACKEND_URL}/groups/invites/{invite_id}/decline", headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def delete_group(group_id: int) -> Dict:
    if MOCK_MODE: return {}
    r = requests.delete(f"{BACKEND_URL}/groups/{group_id}", headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def kick_group_member(group_id: int, user_id: int) -> Dict:
    if MOCK_MODE: return {}
    r = requests.delete(f"{BACKEND_URL}/groups/{group_id}/members/{user_id}", headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def advanced_history() -> Dict:
    if MOCK_MODE: return {"todo": {"solo": [], "group": []}, "history": {"solo": [], "group": []}}
    r = requests.get(f"{BACKEND_URL}/me/advanced_history", headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def save_itinerary(city: str, stops: List[Dict]) -> Dict:
    if MOCK_MODE: return {}
    r = requests.post(f"{BACKEND_URL}/itinerary/save", json={"city": city, "stops": stops}, headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def mark_itinerary_stop(stop_id: int) -> Dict:
    if MOCK_MODE: return {}
    r = requests.post(f"{BACKEND_URL}/itinerary/stop/{stop_id}/visited", headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def get_ai_itinerary(categories: list, city: str) -> dict:
    if MOCK_MODE: return {}
    payload = {"city": city, "categories": categories}
    r = requests.post(f"{BACKEND_URL}/ai/generate-smart-route", json=payload, headers=_headers(), timeout=20)
    _raise(r)
    return r.json()

def get_cities() -> List[str]:
    """Aduce orașele disponibile din DB pentru dropdown."""
    if MOCK_MODE: return ["Iași", "București", "Cluj-Napoca"]
    try:
        r = requests.get(f"{BACKEND_URL}/places/cities", headers=_headers(), timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return ["Iași"]

# ==========================================
# 🧠 AI SECRET SPOTS & CUSTOM LOCATIONS
# ==========================================

def validate_and_add_custom_location(name: str, city: str, rating: int, description: str = "") -> dict:
    """Validează locul cu AI. Dacă description e gol, AI-ul generează textul."""
    if MOCK_MODE: return {"is_valid": True, "message": "Validat de Mock AI"}
    
    # Trimitem corpul cererii către backend formatat corect
    val_payload = {
        "name": name, 
        "city": city, 
        "description": description.strip() if description else ""
    }
    val_req = requests.post(f"{BACKEND_URL}/ai/validate-place", json=val_payload, headers=_headers(), timeout=15)
    _raise(val_req)
    val_data = val_req.json()
    
    if not val_data.get("is_valid"):
        return val_data
        
    ai_desc = f"{val_data.get('description', '')} | Adresă: {val_data.get('address', '')}"
    ai_interval = val_data.get('interval', 'N/A')
    
    # Salvăm în baza de date locală
    save_payload = {
        "name": name, 
        "description": ai_desc, 
        "interval": ai_interval, 
        "rating": rating
    }
    save_req = requests.post(f"{BACKEND_URL}/custom_locations/add", json=save_payload, headers=_headers(), timeout=10)
    _raise(save_req)
    
    return {"is_valid": True, "message": val_data["message"]}

def get_my_custom_locations() -> list:
    if MOCK_MODE: return []
    r = requests.get(f"{BACKEND_URL}/custom_locations/me", headers=_headers(), timeout=10)
    _raise(r)
    return r.json()

def get_cities() -> list:
    if MOCK_MODE: return ["Iași", "București", "Cluj-Napoca"]
    try:
        # Asigură-te că ruta se potrivește cu prefixul tău. Dacă places.py are prefix="/places", pune /places/cities
        r = requests.get(f"{BACKEND_URL}/places/cities", headers=_headers(), timeout=5)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return ["Iași"]  # Fallback vizual în caz de eroare de conexiune
