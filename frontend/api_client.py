"""
Thin HTTP client that every Streamlit page imports.

If MOCK_MODE is on, no network calls are made — useful at H0 when the backend
isn't ready yet. Flip the env var (or edit MOCK_MODE below) once the backend
is up.

Owner: Role 1 writes; everyone uses.
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
                {"place_id": "m1", "name": "Mock Café",  "address": "...",
                 "lat": 47.170, "lon": 27.578, "category": "cafe"},
                {"place_id": "m2", "name": "Mock Park",  "address": "...",
                 "lat": 47.185, "lon": 27.573, "category": "park"},
                {"place_id": "m3", "name": "Mock Museum","address": "...",
                 "lat": 47.157, "lon": 27.588, "category": "museum"},
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
        return {"picks": [
            {"pick_id": 1, "place_name": "Mock Café",  "category": "cafe",
             "city": "Iași", "why": "Cozy and quiet.", "visited": True,
             "created_at": "2026-05-15T10:00:00"},
            {"pick_id": 2, "place_name": "Mock Park",  "category": "park",
             "city": "Iași", "why": "Spring is here.", "visited": True,
             "created_at": "2026-05-14T10:00:00"},
        ]}
    r = requests.get(f"{BACKEND_URL}/me/history",
                     headers=_headers(), params={"limit": limit}, timeout=10)
    _raise(r)
    return r.json()
