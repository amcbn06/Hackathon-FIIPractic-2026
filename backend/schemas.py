"""Pydantic request/response models shared across routers."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, EmailStr


# --- Auth -----------------------------------------------------------------


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    token: str
    user_id: int


class UserOut(BaseModel):
    id: int
    email: str
    display_name: Optional[str] = None
    invite_code: Optional[str] = None
    is_admin: bool = False


# --- Places / picks -------------------------------------------------------


class PickRequest(BaseModel):
    category: str
    city: str
    group_id: Optional[int] = None


class PickResponse(BaseModel):
    pick_id: int
    place_id: str
    name: str
    address: str = ""
    lat: float
    lon: float
    category: str
    city: str
    why: str
    rating: Optional[float] = None
    photo_url: Optional[str] = None
    hours: Optional[str] = None
    visited: bool = False


class PlaceOut(BaseModel):
    id: int
    name: str
    address: str = ""
    lat: float
    lon: float
    category: str
    city: str
    photo_url: Optional[str] = None
    hours: Optional[str] = None
    description: Optional[str] = None
    status: str
    vote_count: int


class SuggestPlaceRequest(BaseModel):
    name: str
    address: Optional[str] = ""
    lat: float
    lon: float
    category: str
    city: str
    hours: Optional[str] = None
    description: Optional[str] = None
    photo_url: Optional[str] = None


# --- Itineraries ----------------------------------------------------------


class ItineraryRequest(BaseModel):
    categories: list[str]
    city: str


class Stop(BaseModel):
    place_id: str
    name: str
    address: str = ""
    lat: float
    lon: float
    category: str


class ItineraryResponse(BaseModel):
    stops: list[Stop]
    total_minutes: int
    insight: Optional[str] = None


class SaveItineraryRequest(BaseModel):
    city: str
    stops: list[dict]


# --- Social ---------------------------------------------------------------


class InviteCodeRequest(BaseModel):
    invite_code: str


class FriendOut(BaseModel):
    user_id: int
    display_name: str
    email: str


class CreateGroupRequest(BaseModel):
    name: str
    member_ids: list[int] = []


class GroupMemberDetail(BaseModel):
    user_id: int
    display_name: str
    invite_code: Optional[str] = None


class GroupOut(BaseModel):
    group_id: int
    name: str
    owner_id: int
    member_ids: list[int]
    members: list[GroupMemberDetail] = []


class GroupPickRequest(BaseModel):
    category: str
    city: str


class GroupInviteOut(BaseModel):
    invite_id: int
    group_id: int
    group_name: str
    sender_name: str


# --- Gamification ---------------------------------------------------------


class StreakOut(BaseModel):
    current: int
    longest: int
    last_visit_date: Optional[str] = None


class CalendarDay(BaseModel):
    date: str
    visited: bool


class HistoryItem(BaseModel):
    pick_id: int
    place_name: str
    category: str
    city: str
    why: str
    visited: bool
    created_at: Optional[str] = None


class HistoryOut(BaseModel):
    picks: list[HistoryItem]


# --- Custom spots ---------------------------------------------------------


class CustomLocationRequest(BaseModel):
    name: str
    city: str
    rating: int = 5
    description: Optional[str] = ""


class CustomLocationOut(BaseModel):
    id: int
    name: str
    description: str
    address: Optional[str] = None
    interval: Optional[str] = None
    rating: int
    ai_generated: bool
    created_at: Optional[str] = None
