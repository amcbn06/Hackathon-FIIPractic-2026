"""Streak + history + a combined tracker (to-do / done)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import (
    Group,
    GroupCheckin,
    GroupMember,
    Itinerary,
    ItineraryStop,
    Pick,
    Streak,
    User,
)
from backend.schemas import CalendarDay, HistoryItem, HistoryOut, StreakOut

router = APIRouter(tags=["gamification"])


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


@router.get("/me/streak/calendar", response_model=list[CalendarDay])
def streak_calendar(
    days: int = 30,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cutoff = datetime.utcnow() - timedelta(days=days)
    picks = (
        db.query(Pick)
        .filter(
            Pick.user_id == user.id,
            Pick.visited_at.isnot(None),
            Pick.visited_at >= cutoff,
        )
        .all()
    )
    visited = {p.visited_at.date() for p in picks}
    return [
        CalendarDay(
            date=(date.today() - timedelta(days=i)).isoformat(),
            visited=(date.today() - timedelta(days=i)) in visited,
        )
        for i in range(days)
    ]


@router.get("/me/history", response_model=HistoryOut)
def history(
    visited_only: bool = False,
    category: Optional[str] = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Pick).filter(Pick.user_id == user.id)
    if visited_only:
        q = q.filter(Pick.visited_at.isnot(None))
    if category:
        q = q.filter(Pick.category == category)
    picks = q.order_by(Pick.created_at.desc()).limit(limit).all()
    return HistoryOut(
        picks=[
            HistoryItem(
                pick_id=p.id,
                place_name=p.place_name,
                category=p.category,
                city=p.city,
                why=p.why or "",
                visited=p.visited_at is not None,
                created_at=p.created_at.isoformat() if p.created_at else None,
            )
            for p in picks
            if p.place_name
        ]
    )


@router.get("/me/tracker")
def tracker(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Everything split into to-do vs history: solo picks, group picks, itineraries."""
    # Solo picks
    solo = (
        db.query(Pick)
        .filter(Pick.user_id == user.id, Pick.group_id.is_(None))
        .order_by(Pick.created_at.desc())
        .all()
    )
    todo_solo, hist_solo = [], []
    for p in solo:
        item = {
            "pick_id": p.id,
            "place_name": p.place_name,
            "category": p.category,
            "city": p.city,
        }
        (hist_solo if p.visited_at else todo_solo).append(item)

    # Group picks
    group_ids = [
        gm.group_id
        for gm in db.query(GroupMember).filter(GroupMember.user_id == user.id).all()
    ]
    group_picks = (
        db.query(Pick)
        .filter(Pick.group_id.in_(group_ids))
        .order_by(Pick.created_at.desc())
        .all()
        if group_ids
        else []
    )
    todo_group, hist_group = [], []
    for p in group_picks:
        group = db.query(Group).filter(Group.id == p.group_id).first()
        total = len(group.members) if group else 1
        checked = [
            c.user_id
            for c in db.query(GroupCheckin).filter(GroupCheckin.pick_id == p.id).all()
        ]
        item = {
            "pick_id": p.id,
            "place_name": p.place_name,
            "category": p.category,
            "group_name": group.name if group else "Group",
            "total_members": total,
            "checked_in_count": len(checked),
            "i_checked_in": user.id in checked,
        }
        (hist_group if p.visited_at else todo_group).append(item)

    # Itineraries
    itineraries = db.query(Itinerary).filter(Itinerary.user_id == user.id).all()
    todo_itin, hist_itin = [], []
    for itin in itineraries:
        stops = (
            db.query(ItineraryStop)
            .filter(ItineraryStop.itinerary_id == itin.id)
            .order_by(ItineraryStop.position)
            .all()
        )
        visited = sum(1 for s in stops if s.visited_at)
        data = {
            "itinerary_id": itin.id,
            "city": itin.city,
            "created_at": itin.created_at.strftime("%d %b %Y")
            if itin.created_at
            else "Recent",
            "total_stops": len(stops),
            "visited_stops": visited,
            "stops": [
                {
                    "stop_id": s.id,
                    "place_name": s.place_name,
                    "category": s.category,
                    "visited": bool(s.visited_at),
                }
                for s in stops
            ],
        }
        done = itin.completed_at or (stops and visited == len(stops))
        (hist_itin if done else todo_itin).append(data)

    return {
        "todo": {"solo": todo_solo, "group": todo_group, "itineraries": todo_itin},
        "history": {"solo": hist_solo, "group": hist_group, "itineraries": hist_itin},
    }
