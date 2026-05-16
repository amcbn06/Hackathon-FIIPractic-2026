"""
Seed the demo database with two accounts, a friendship, a group, and
fake streaks. Run before the live demo so screens never look empty.

Usage:
    python -m backend.tests.seed
"""

from datetime import date, timedelta
import secrets

from backend.db import (
    init_db, SessionLocal, User, Friendship, Group, GroupMember,
    Streak, Pick,
)
from backend.auth import hash_password


DEMO_ACCOUNTS = [
    {"email": "demo@onepick.app",  "password": "demo1234", "name": "Demo User"},
    {"email": "ana@onepick.app",   "password": "demo1234", "name": "Ana"},
]


def run():
    init_db()
    db = SessionLocal()
    try:
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

        # Friendship between the two demo accounts
        a, b = sorted([users[0].id, users[1].id])
        if not db.query(Friendship).filter(
            Friendship.user_a_id == a, Friendship.user_b_id == b
        ).first():
            db.add(Friendship(user_a_id=a, user_b_id=b, status="accepted"))

        # A demo group containing both
        g = db.query(Group).filter(Group.name == "Weekend Crew").first()
        if not g:
            g = Group(name="Weekend Crew", owner_id=users[0].id)
            db.add(g)
            db.flush()
            for u in users:
                db.add(GroupMember(group_id=g.id, user_id=u.id))

        # Streaks so the UI looks alive
        for i, u in enumerate(users):
            s = db.query(Streak).filter(Streak.user_id == u.id).first()
            if not s:
                s = Streak(user_id=u.id)
                db.add(s)
            s.current = 7 if i == 0 else 3
            s.longest = 12 if i == 0 else 5
            s.last_visit_date = date.today() - timedelta(days=0 if i == 0 else 1)

        # A few past picks for history
        if not db.query(Pick).filter(Pick.user_id == users[0].id).first():
            for cat in ["cafe", "park", "museum"]:
                db.add(Pick(
                    user_id=users[0].id, place_id=f"seed-{cat}",
                    place_name=f"Seeded {cat.title()}",
                    category=cat, city="Iași",
                    why=f"You haven't tried a {cat} this week.",
                ))

        db.commit()
        print(f"Seeded {len(users)} accounts. Invite codes:")
        for u in users:
            print(f"  {u.email} -> {u.invite_code} (password: demo1234)")
    finally:
        db.close()


if __name__ == "__main__":
    run()
