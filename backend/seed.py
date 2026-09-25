"""
Seed the demo database.

Creates two demo accounts (a friendship, a group, streaks and some history)
and loads every curated place from data/seed_places.json.

Usage:
    python -m backend.seed
    python -m backend.seed --reset     # wipe places + picks first
"""

from __future__ import annotations

import json
import secrets
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from backend.auth import hash_password
from backend.database import SessionLocal, init_db
from backend.models import (
    PLACE_ADMIN,
    Friendship,
    Group,
    GroupMember,
    Pick,
    Place,
    Streak,
    User,
)

SEED_FILE = Path(__file__).resolve().parent / "data" / "seed_places.json"

DEMO_ACCOUNTS = [
    {"email": "demo@onepick.app", "password": "demo1234", "name": "Demo User"},
    {"email": "ana@onepick.app", "password": "demo1234", "name": "Ana"},
]


def _seed_users(db) -> list[User]:
    users = []
    for acc in DEMO_ACCOUNTS:
        u = db.query(User).filter(User.email == acc["email"]).first()
        if not u:
            u = User(
                email=acc["email"],
                password_hash=hash_password(acc["password"]),
                display_name=acc["name"],
                invite_code=secrets.token_hex(3).upper(),
            )
            db.add(u)
            db.flush()
        users.append(u)
    return users


def _seed_social(db, users) -> None:
    a, b = sorted([users[0].id, users[1].id])
    if not db.query(Friendship).filter_by(user_a_id=a, user_b_id=b).first():
        db.add(Friendship(user_a_id=a, user_b_id=b, status="accepted"))

    if not db.query(Group).filter(Group.name == "Weekend Crew").first():
        g = Group(name="Weekend Crew", owner_id=users[0].id)
        db.add(g)
        db.flush()
        for u in users:
            db.add(GroupMember(group_id=g.id, user_id=u.id))


def _seed_streaks(db, users) -> None:
    for i, u in enumerate(users):
        s = db.query(Streak).filter(Streak.user_id == u.id).first()
        if not s:
            s = Streak(user_id=u.id)
            db.add(s)
        s.current = 7 if i == 0 else 3
        s.longest = 12 if i == 0 else 5
        s.last_visit_date = date.today() - timedelta(days=0 if i == 0 else 1)


def _seed_places(db, reset: bool) -> int:
    if reset:
        db.query(Pick).delete()
        db.query(Place).delete()
        db.commit()

    if not SEED_FILE.exists():
        print(f"  WARN: {SEED_FILE} not found — skipping places")
        return 0

    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    inserted = 0
    for entry in data.get("places", []):
        exists = (
            db.query(Place)
            .filter(Place.name == entry["name"], Place.city == entry["city"])
            .first()
        )
        if exists:
            continue
        db.add(
            Place(
                name=entry["name"],
                address=entry.get("address", ""),
                lat=entry["lat"],
                lon=entry["lon"],
                category=entry["category"],
                city=entry["city"],
                hours=entry.get("hours"),
                description=entry.get("description"),
                photo_url=entry.get("photo_url"),
                status=PLACE_ADMIN,
                vote_count=0,
            )
        )
        inserted += 1
    db.commit()
    return inserted


def _seed_history(db, users) -> None:
    if db.query(Pick).filter(Pick.user_id == users[0].id).count() > 0:
        return
    sample = db.query(Place).filter(Place.status == PLACE_ADMIN).limit(7).all()
    today = date.today()
    for i, place in enumerate(sample):
        past = today - timedelta(days=i + 1)
        visited = (
            datetime.combine(past, datetime.min.time()) + timedelta(hours=14)
            if i < 5
            else None
        )
        db.add(
            Pick(
                user_id=users[0].id,
                place_id=str(place.id),
                place_name=place.name,
                category=place.category,
                city=place.city,
                why=place.description or f"A great {place.category}.",
                created_at=datetime.combine(past, datetime.min.time())
                + timedelta(hours=10),
                visited_at=visited,
            )
        )


def run(reset: bool = False) -> None:
    init_db()
    db = SessionLocal()
    try:
        users = _seed_users(db)
        db.commit()
        _seed_social(db, users)
        _seed_streaks(db, users)
        n = _seed_places(db, reset)
        _seed_history(db, users)
        db.commit()

        print(f"Seeded {len(users)} accounts and {n} new places.")
        for u in users:
            print(f"  {u.email} -> invite {u.invite_code} (password: demo1234)")
    finally:
        db.close()


if __name__ == "__main__":
    run(reset="--reset" in sys.argv)
