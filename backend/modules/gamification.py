"""
Streaks + history.

Owner: Role 3.

Endpoints:
    GET /me/streak       -> current + longest streak, last visit date
    GET /me/history      -> paginated past picks
"""

from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import User, Pick, Streak, get_db

router = APIRouter(tags=["gamification"])


class StreakOut(BaseModel):
    current: int
    longest: int
    last_visit_date: Optional[str] = None


class HistoryItem(BaseModel):
    pick_id: int
    place_name: str
    category: str
    city: str
    why: str
    visited: bool
    created_at: str


class HistoryOut(BaseModel):
    picks: List[HistoryItem]


@router.get("/me/streak", response_model=StreakOut)
def get_streak(user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    s = db.query(Streak).filter(Streak.user_id == user.id).first()
    if not s:
        return StreakOut(current=0, longest=0, last_visit_date=None)
    return StreakOut(
        current=s.current,
        longest=s.longest,
        last_visit_date=s.last_visit_date.isoformat() if s.last_visit_date else None,
    )


@router.get("/me/history", response_model=HistoryOut)
def get_history(user: User = Depends(get_current_user),
                db: Session = Depends(get_db), limit: int = 50):
    picks = (db.query(Pick)
               .filter(Pick.user_id == user.id)
               .order_by(Pick.created_at.desc())
               .limit(limit).all())
    return HistoryOut(picks=[
        HistoryItem(
            pick_id=p.id,
            place_name=p.place_name,
            category=p.category,
            city=p.city,
            why=p.why or "",
            visited=p.visited_at is not None,
            created_at=p.created_at.isoformat(),
        ) for p in picks
    ])
