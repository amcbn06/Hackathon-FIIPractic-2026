"""
Pick + itinerary endpoints.

Owner: Role 2.

Endpoints:
    POST /pick                       -> one recommendation
    POST /pick/{id}/reroll           -> reroll an existing pick (max 3/day)
    POST /pick/{id}/visited          -> mark visited (increments streak)
    POST /pick/{id}/thumbs           -> +1 / -1 crowdsourced signal
    POST /itinerary                  -> multi-stop route
"""

import os
import random
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db import User, Pick, Streak, get_db
from backend.modules.geoapify_client import search_places

router = APIRouter(tags=["places"])

DAILY_REROLL_LIMIT = 3


# ----- Schemas --------------------------------------------------------------

class PickRequest(BaseModel):
    category: str
    city: str
    group_id: Optional[int] = None


class PickResponse(BaseModel):
    pick_id: int
    place_id: str
    name: str
    address: str
    lat: float
    lon: float
    why: str
    rating: Optional[float] = None
    photo_url: Optional[str] = None
    hours: Optional[str] = None


class ItineraryRequest(BaseModel):
    categories: List[str]
    city: str
    day: Optional[str] = None    # ISO date string, optional


class Stop(BaseModel):
    place_id: str
    name: str
    address: str
    lat: float
    lon: float
    category: str


class ItineraryResponse(BaseModel):
    stops: List[Stop]
    total_minutes: int


# ----- Core picking logic ---------------------------------------------------

def _weight(place: dict, seen_place_ids: set) -> float:
    """
    Score a candidate. Higher = more likely to be picked.

    Weighted sum of:
      - rating (0-5)
      - novelty bonus if user hasn't seen this place recently
      - small randomness so identical inputs don't always yield the same pick
    """
    rating = place.get("rating") or 3.5     # neutral default
    novelty = 0.0 if place["place_id"] in seen_place_ids else 1.5
    jitter = random.uniform(0, 0.5)
    return rating + novelty + jitter


def _generate_reason(place: dict, category: str) -> str:
    """
    Generate a one-line "why this pick" reason.

    Tries Anthropic Claude first; falls back to a template string if the API
    key isn't set or the call fails. Role 2 + Role 5 tune the prompt.
    """
    template = f"Top-rated {category} nearby"
    if place.get("hours"):
        template += f" — open {place['hours']}"

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return template

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=60,
            messages=[{
                "role": "user",
                "content": (
                    f"Write ONE short sentence (max 18 words) telling a student "
                    f"why they should visit this {category}: "
                    f"name={place['name']}, address={place.get('address','')}, "
                    f"hours={place.get('hours','')}, rating={place.get('rating','?')}. "
                    f"No emoji. No exclamation marks. Friendly but not breathless."
                ),
            }],
        )
        return msg.content[0].text.strip()
    except Exception:
        return template


def _pick_for_user(db: Session, user_id: int, category: str, city: str) -> dict:
    candidates = search_places(category, city)
    if not candidates:
        raise HTTPException(status_code=404, detail="No places found")

    seen = {
        p.place_id for p in db.query(Pick)
        .filter(Pick.user_id == user_id).limit(50).all()
    }
    scored = sorted(candidates, key=lambda p: _weight(p, seen), reverse=True)
    chosen = scored[0]
    chosen["why"] = _generate_reason(chosen, category)
    return chosen


# ----- Routes ---------------------------------------------------------------

@router.post("/pick", response_model=PickResponse)
def pick(body: PickRequest, user: User = Depends(get_current_user),
         db: Session = Depends(get_db)):
    chosen = _pick_for_user(db, user.id, body.category, body.city)
    p = Pick(
        user_id=user.id,
        group_id=body.group_id,
        place_id=chosen["place_id"],
        place_name=chosen["name"],
        category=body.category,
        city=body.city,
        why=chosen["why"],
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return PickResponse(
        pick_id=p.id,
        place_id=chosen["place_id"],
        name=chosen["name"],
        address=chosen.get("address", ""),
        lat=chosen["lat"],
        lon=chosen["lon"],
        why=chosen["why"],
        rating=chosen.get("rating"),
        photo_url=chosen.get("photo_url"),
        hours=chosen.get("hours"),
    )


@router.post("/pick/{pick_id}/reroll", response_model=PickResponse)
def reroll(pick_id: int, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    p = db.query(Pick).filter(Pick.id == pick_id, Pick.user_id == user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pick not found")

    today_rerolls = db.query(Pick).filter(
        Pick.user_id == user.id,
        Pick.created_at >= datetime.combine(date.today(), datetime.min.time()),
        Pick.reroll_count > 0,
    ).count()
    if today_rerolls >= DAILY_REROLL_LIMIT:
        raise HTTPException(status_code=429, detail="Daily reroll limit hit")

    chosen = _pick_for_user(db, user.id, p.category, p.city)
    p.place_id = chosen["place_id"]
    p.place_name = chosen["name"]
    p.why = chosen["why"]
    p.reroll_count += 1
    db.commit()
    return PickResponse(
        pick_id=p.id,
        place_id=chosen["place_id"],
        name=chosen["name"],
        address=chosen.get("address", ""),
        lat=chosen["lat"],
        lon=chosen["lon"],
        why=chosen["why"],
        rating=chosen.get("rating"),
        photo_url=chosen.get("photo_url"),
        hours=chosen.get("hours"),
    )


@router.post("/pick/{pick_id}/visited")
def mark_visited(pick_id: int, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    p = db.query(Pick).filter(Pick.id == pick_id, Pick.user_id == user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pick not found")
    if p.visited_at is None:
        p.visited_at = datetime.utcnow()

    # Streak handoff to gamification module would be cleaner, but for the MVP
    # we update it inline.
    streak = db.query(Streak).filter(Streak.user_id == user.id).first()
    today = date.today()
    if not streak:
        streak = Streak(user_id=user.id, current=1, longest=1, last_visit_date=today)
        db.add(streak)
    else:
        if streak.last_visit_date == today:
            pass  # already counted today
        elif streak.last_visit_date and (today - streak.last_visit_date).days == 1:
            streak.current += 1
            streak.longest = max(streak.longest, streak.current)
            streak.last_visit_date = today
        else:
            streak.current = 1
            streak.last_visit_date = today
    db.commit()
    return {"streak_current": streak.current, "streak_longest": streak.longest}


@router.post("/pick/{pick_id}/thumbs")
def thumbs(pick_id: int, value: int,
           user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    """Crowdsourced overlay signal: +1 worth it, -1 skip it."""
    if value not in (-1, 0, 1):
        raise HTTPException(status_code=400, detail="value must be -1, 0, or 1")
    p = db.query(Pick).filter(Pick.id == pick_id, Pick.user_id == user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pick not found")
    p.thumbs = value
    db.commit()
    return {"thumbs": value}


@router.post("/itinerary", response_model=ItineraryResponse)
def itinerary(body: ItineraryRequest,
              user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    """
    Greedy itinerary: for each requested category, pick the best place,
    then order them nearest-neighbor style starting from the first stop.
    """
    stops_raw = []
    for cat in body.categories:
        candidates = search_places(cat, body.city)
        if candidates:
            stops_raw.append((cat, candidates[0]))

    if not stops_raw:
        raise HTTPException(status_code=404, detail="No places found")

    # Greedy nearest-neighbor ordering
    ordered = [stops_raw[0]]
    remaining = stops_raw[1:]
    while remaining:
        last = ordered[-1][1]
        remaining.sort(key=lambda x: (x[1]["lat"] - last["lat"])**2
                                     + (x[1]["lon"] - last["lon"])**2)
        ordered.append(remaining.pop(0))

    stops = [
        Stop(
            place_id=p["place_id"],
            name=p["name"],
            address=p.get("address", ""),
            lat=p["lat"],
            lon=p["lon"],
            category=cat,
        )
        for cat, p in ordered
    ]
    # Rough estimate: 30 min per stop + 10 min travel between
    total = 30 * len(stops) + 10 * max(0, len(stops) - 1)
    return ItineraryResponse(stops=stops, total_minutes=total)
