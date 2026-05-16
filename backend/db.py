"""
SQLAlchemy models + DB session.

Owner: Role 1 (Tech Lead).
Everyone imports `SessionLocal` and the models they need from here.
Do not import this module from outside backend/.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Date,
    create_engine, UniqueConstraint, CheckConstraint,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# Anchor the DB path to the project root (parent of backend/) so the file
# lives in a predictable place no matter where uvicorn / streamlit / pytest
# is launched from. Override with DATABASE_URL env var for prod deploys.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "onepick.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}, echo=False
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    invite_code = Column(String, unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    picks = relationship("Pick", back_populates="user", cascade="all, delete-orphan")
    streak = relationship("Streak", back_populates="user", uselist=False,
                          cascade="all, delete-orphan")


class PlaceCache(Base):
    __tablename__ = "places_cache"
    id = Column(Integer, primary_key=True)
    category = Column(String, index=True)
    city = Column(String, index=True)
    place_id = Column(String, index=True)
    name = Column(String)
    address = Column(String)
    lat = Column(Float)
    lon = Column(Float)
    rating = Column(Float, nullable=True)
    photo_url = Column(String, nullable=True)
    hours = Column(String, nullable=True)
    raw_json = Column(String)
    cached_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    visited_at = Column(DateTime, nullable=True)
    reroll_count = Column(Integer, default=0)
    thumbs = Column(Integer, default=0)
    user = relationship("User", back_populates="picks")


class Friendship(Base):
    __tablename__ = "friendships"
    id = Column(Integer, primary_key=True)
    user_a_id = Column(Integer, ForeignKey("users.id"))
    user_b_id = Column(Integer, ForeignKey("users.id"))
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # add this
    status = Column(String, default="pending")  # change default from "accepted"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    members = relationship("GroupMember", back_populates="group",
                           cascade="all, delete-orphan")


class GroupMember(Base):
    __tablename__ = "group_members"
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_member"),)
    group = relationship("Group", back_populates="members")


class Streak(Base):
    __tablename__ = "streaks"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True)
    current = Column(Integer, default=0)
    longest = Column(Integer, default=0)
    last_visit_date = Column(Date, nullable=True)
    user = relationship("User", back_populates="streak")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
