"""
Seed the demo database with:
  - Two demo user accounts (with a friendship, a group, streaks, history)
  - All admin-curated places from seed_places.json (status='admin')

Idempotent — running it twice doesn't duplicate rows.

Usage:
    python -m backend.tests.seed
"""

import json
import secrets
from datetime import date, timedelta
from pathlib import Path

from backend.db import (
    init_db, SessionLocal, User, Friendship, Group, GroupMember,
    Streak, Pick, Place,
)
from backend.auth import hash_password


DEMO_ACCOUNTS = [
    {"email": "demo@onepick.app",  "password": "demo1234", "name": "Demo User"},
    {"email": "ana@onepick.app",   "password": "demo1234", "name": "Ana"},
]

SEED_PLACES_FILE = Path(__file__).resolve().parent.parent / "seed_places.json"


def _seed_users(db):
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


def _seed_social(db, users):
    a, b = sorted([users[0].id, users[1].id])
    if not db.query(Friendship).filter(
        Friendship.user_a_id == a, Friendship.user_b_id == b
    ).first():
        db.add(Friendship(user_a_id=a, user_b_id=b, status="accepted"))

    g = db.query(Group).filter(Group.name == "Weekend Crew").first()
    if not g:
        g = Group(name="Weekend Crew", owner_id=users[0].id)
        db.add(g)
        db.flush()
        for u in users:
            db.add(GroupMember(group_id=g.id, user_id=u.id))


def _seed_streaks(db, users):
    for i, u in enumerate(users):
        s = db.query(Streak).filter(Streak.user_id == u.id).first()
        if not s:
            s = Streak(user_id=u.id)
            db.add(s)
        s.current = 7 if i == 0 else 3
        s.longest = 12 if i == 0 else 5
        s.last_visit_date = date.today() - timedelta(days=0 if i == 0 else 1)


def _seed_places(db) -> int:
    """Load seed_places.json and upsert into the Place table with status='admin'."""
    if not SEED_PLACES_FILE.exists():
        print(f"  WARN: {SEED_PLACES_FILE} not found, skipping place seeding")
        return 0

    data = json.loads(SEED_PLACES_FILE.read_text(encoding="utf-8"))
    inserted = 0
    for entry in data.get("places", []):
        # Idempotency key: (name, city). If a place with the same name+city
        # already exists, leave it alone.
        existing = db.query(Place).filter(
            Place.name == entry["name"], Place.city == entry["city"]
        ).first()
        if existing:
            continue
        db.add(Place(
            name=entry["name"],
            address=entry.get("address", ""),
            lat=entry["lat"], lon=entry["lon"],
            category=entry["category"], city=entry["city"],
            hours=entry.get("hours"),
            description=entry.get("description"),
            photo_url=entry.get("photo_url"),
            status="admin",
            vote_count=0,
        ))
        inserted += 1
    return inserted


def _seed_history(db, users):
    """Give the demo user some history. References real seeded places when available."""
    if db.query(Pick).filter(Pick.user_id == users[0].id).first():
        return
    sample = db.query(Place).filter(Place.status == "admin").limit(3).all()
    for i, place in enumerate(sample):
        db.add(Pick(
            user_id=users[0].id,
            place_id=str(place.id),
            place_name=place.name,
            category=place.category,
            city=place.city,
            why=place.description or f"A solid local {place.category}.",
            visited_at=None if i == 0 else None,
        ))


def run():
    init_db()
    db = SessionLocal()
    try:
        users = _seed_users(db)
        _seed_social(db, users)
        _seed_streaks(db, users)
        n_places = _seed_places(db)
        _seed_history(db, users)
        db.commit()

        print(f"Seeded {len(users)} accounts, {n_places} new admin places.")
        print(f"Invite codes:")
        for u in users:
            print(f"  {u.email} -> {u.invite_code} (password: demo1234)")
        if n_places:
            print(f"\nTip: set ADMIN_EMAILS=demo@onepick.app in .env to make demo@ an admin.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
