"""
ORM models for OnePick.

The domain in one breath: users get *one* recommendation (a Pick) for a chosen
vibe + city, drawn from a crowdsourced Place catalogue. Visiting a Pick feeds a
Streak. Users befriend each other by invite code, form Groups, and can build
multi-stop Itineraries.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from backend.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- Places ---------------------------------------------------------------

# status values a Place can hold
PLACE_ADMIN = "admin"        # seeded / curated, always eligible
PLACE_PENDING = "pending"    # user-submitted, awaiting community votes
PLACE_APPROVED = "approved"  # promoted after enough votes
PLACE_REJECTED = "rejected"  # rejected by an admin

ELIGIBLE_STATUSES = (PLACE_ADMIN, PLACE_APPROVED)


class Place(Base):
    __tablename__ = "places"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    address = Column(String, default="")
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    category = Column(String, index=True, nullable=False)
    city = Column(String, index=True, nullable=False)
    photo_url = Column(String, nullable=True)
    hours = Column(String, nullable=True)
    description = Column(String, nullable=True)
    vote_count = Column(Integer, default=0, nullable=False)
    status = Column(String, default=PLACE_PENDING, nullable=False, index=True)
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    votes = relationship(
        "PlaceVote", back_populates="place", cascade="all, delete-orphan"
    )


class PlaceVote(Base):
    __tablename__ = "place_votes"

    id = Column(Integer, primary_key=True)
    place_id = Column(Integer, ForeignKey("places.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    created_at = Column(DateTime, default=_utcnow)

    __table_args__ = (UniqueConstraint("place_id", "user_id", name="uq_place_vote"),)
    place = relationship("Place", back_populates="votes")


# --- Users & auth ---------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    invite_code = Column(String, unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=_utcnow)

    picks = relationship(
        "Pick", back_populates="user", cascade="all, delete-orphan"
    )
    streak = relationship(
        "Streak", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


# --- Picks ----------------------------------------------------------------


class Pick(Base):
    __tablename__ = "picks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    place_id = Column(String)
    place_name = Column(String)
    category = Column(String)
    city = Column(String)
    why = Column(String)
    created_at = Column(DateTime, default=_utcnow)
    visited_at = Column(DateTime, nullable=True)
    reroll_count = Column(Integer, default=0)
    thumbs = Column(Integer, default=0)

    user = relationship("User", back_populates="picks")


# --- Social ---------------------------------------------------------------


class Friendship(Base):
    __tablename__ = "friendships"

    id = Column(Integer, primary_key=True)
    # user_a_id < user_b_id always, so a pair has exactly one row
    user_a_id = Column(Integer, ForeignKey("users.id"))
    user_b_id = Column(Integer, ForeignKey("users.id"))
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="pending")  # pending | accepted | blocked
    created_at = Column(DateTime, default=_utcnow)

    __table_args__ = (
        UniqueConstraint("user_a_id", "user_b_id", name="uq_friendship_pair"),
    )


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=_utcnow)

    members = relationship(
        "GroupMember", back_populates="group", cascade="all, delete-orphan"
    )


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)

    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_member"),)
    group = relationship("Group", back_populates="members")


class GroupInvite(Base):
    __tablename__ = "group_invites"

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"))
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="pending")  # pending | accepted | declined
    created_at = Column(DateTime, default=_utcnow)


class GroupCheckin(Base):
    __tablename__ = "group_checkins"

    id = Column(Integer, primary_key=True)
    pick_id = Column(Integer, ForeignKey("picks.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=_utcnow)

    __table_args__ = (UniqueConstraint("pick_id", "user_id", name="uq_checkin"),)


# --- Gamification ---------------------------------------------------------


class Streak(Base):
    __tablename__ = "streaks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True)
    current = Column(Integer, default=0)
    longest = Column(Integer, default=0)
    last_visit_date = Column(Date, nullable=True)

    user = relationship("User", back_populates="streak")


# --- Itineraries ----------------------------------------------------------


class Itinerary(Base):
    __tablename__ = "itineraries"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    city = Column(String)
    created_at = Column(DateTime, default=_utcnow)
    completed_at = Column(DateTime, nullable=True)

    stops = relationship(
        "ItineraryStop", cascade="all, delete-orphan", backref="itinerary"
    )


class ItineraryStop(Base):
    __tablename__ = "itinerary_stops"

    id = Column(Integer, primary_key=True)
    itinerary_id = Column(Integer, ForeignKey("itineraries.id"))
    place_id = Column(String)
    place_name = Column(String)
    category = Column(String)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    position = Column(Integer, default=0)
    visited_at = Column(DateTime, nullable=True)


# --- Custom "secret spots" ------------------------------------------------


class CustomLocation(Base):
    __tablename__ = "custom_locations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    description = Column(String)
    address = Column(String, nullable=True)
    interval = Column(String)
    rating = Column(Integer)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    ai_generated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)
