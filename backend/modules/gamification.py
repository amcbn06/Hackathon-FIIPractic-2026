"""
Streaks + history.
Owner: Role 3.
"""
from typing import List, Optional
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import User, Pick, Streak, get_db

router = APIRouter(tags=["gamification"])

def increment_streak(db: Session, user_id: int) -> Streak:
    streak = db.query(Streak).filter(Streak.user_id == user_id).first()
    today = date.today()
    if not streak:
        streak = Streak(user_id=user_id, current=1, longest=1, last_visit_date=today)
        db.add(streak)
    else:
        if streak.last_visit_date == today:
            pass
        elif streak.last_visit_date and (today - streak.last_visit_date).days == 1:
            streak.current += 1
            streak.longest = max(streak.longest, streak.current)
            streak.last_visit_date = today
        else:
            streak.current = 1
            streak.last_visit_date = today
    db.commit()
    db.refresh(streak)
    return streak

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
    created_at: str

class HistoryOut(BaseModel):
    picks: List[HistoryItem]

@router.get("/me/streak", response_model=StreakOut)
def get_streak(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(Streak).filter(Streak.user_id == user.id).first()
    if not s:
        return StreakOut(current=0, longest=0, last_visit_date=None)
    return StreakOut(
        current=s.current,
        longest=s.longest,
        last_visit_date=s.last_visit_date.isoformat() if s.last_visit_date else None,
    )

@router.get("/me/streak/calendar", response_model=List[CalendarDay])
def get_streak_calendar(days: int = 30, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(days=days)
    picks = db.query(Pick).filter(
        Pick.user_id == user.id, 
        Pick.visited_at.isnot(None),
        Pick.visited_at >= cutoff
    ).all()
    visited_dates = {p.visited_at.date() for p in picks}
    return [CalendarDay(date=(date.today() - timedelta(days=i)).isoformat(), visited=((date.today() - timedelta(days=i)) in visited_dates)) for i in range(days)]

@router.get("/me/history", response_model=HistoryOut)
def get_history(visited_only: bool = False, category: Optional[str] = None, limit: int = 50, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Pick).filter(Pick.user_id == user.id)
    if visited_only:
        query = query.filter(Pick.visited_at.isnot(None))
    if category:
        query = query.filter(Pick.category == category)
    picks = query.order_by(Pick.created_at.desc()).limit(limit).all()
    return HistoryOut(picks=[
        HistoryItem(pick_id=p.id, place_name=p.place_name, category=p.category, city=p.city, why=p.why or "", visited=p.visited_at is not None, created_at=p.created_at.isoformat()) for p in picks
    ])