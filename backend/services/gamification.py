"""Streak bookkeeping."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from backend.models import Streak


def increment_streak(db: Session, user_id: int) -> Streak:
    """Bump the user's streak for a visit today.

    Same-day visits are idempotent; a visit the day after a previous one
    extends the streak; any longer gap resets it to 1.
    """
    streak = db.query(Streak).filter(Streak.user_id == user_id).first()
    today = date.today()

    if not streak:
        streak = Streak(user_id=user_id, current=1, longest=1, last_visit_date=today)
        db.add(streak)
    elif streak.last_visit_date == today:
        pass  # already counted today
    elif streak.last_visit_date and (today - streak.last_visit_date).days == 1:
        streak.current += 1
        streak.longest = max(streak.longest or 0, streak.current)
        streak.last_visit_date = today
    else:
        streak.current = 1
        streak.longest = max(streak.longest or 0, 1)
        streak.last_visit_date = today

    db.commit()
    db.refresh(streak)
    return streak
