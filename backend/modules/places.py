"""
Pick + itinerary endpoints + crowdsourced places CRUD.

Owner: Role 2.

Endpoints:
    Picking:
      POST   /pick                       -> one recommendation
      POST   /pick/{id}/reroll           -> reroll an existing pick (max 3/day)
      POST   /pick/{id}/visited          -> m  ark visited (increments streak)
      POST   /pick/{id}/thumbs           -> +1 / -1 crowdsourced signal
      POST   /itinerary                  -> multi-stop route

    Places (crowdsourced + admin-seeded):
      GET    /places                     -> list approved + admin places
      GET    /places/pending             -> list pending (for voting)
      GET    /places/{id}                -> place detail
      POST   /places/suggest             -> user submits a new place
      POST   /places/{id}/vote           -> upvote (auto-promotes at threshold)
      POST   /places/{id}/approve        -> admin force-approves
      POST   /places/{id}/reject         -> admin rejects
      DELETE /places/{id}                -> admin only

Pick source: queries the Place table directly. status in ('admin', 'approved')
is eligible for /pick. Falls back to status='admin' only if no approved places
exist for the category+city.
"""

import os
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from opening_hours import OpeningHours
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user, get_admin_user
from backend.db import User, Pick, Streak, Place, PlaceVote, get_db

router = APIRouter(tags=["places"])

DAILY_REROLL_LIMIT = 3
PLACE_PROMOTION_VOTES = int(os.getenv("PLACE_PROMOTION_VOTES", "3"))
USE_ANTHROPIC = os.getenv("USE_ANTHROPIC", "false").lower() == "true"


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
    day: Optional[str] = None


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


class PlaceOut(BaseModel):
    id: int
    name: str
    address: str
    lat: float
    lon: float
    category: str
    city: str
    photo_url: Optional[str] = None
    hours: Optional[str] = None
    description: Optional[str] = None
    status: str
    vote_count: int


class SuggestPlaceRequest(BaseModel):
    name: str
    address: Optional[str] = ""
    lat: float
    lon: float
    category: str
    city: str
    hours: Optional[str] = None
    description: Optional[str] = None
    photo_url: Optional[str] = None


# ----- Helpers --------------------------------------------------------------

def _place_to_dict(p: Place) -> dict:
    """Serialize a Place ORM row into the dict shape the picking logic expects."""
    return {
        "place_id": str(p.id),
        "name": p.name,
        "address": p.address or "",
        "lat": p.lat,
        "lon": p.lon,
        "category": p.category,
        "city": p.city,
        "photo_url": p.photo_url,
        "hours": p.hours,
        "description": p.description,
        "rating": None,         # no external rating in crowdsourced mode
        "vote_count": p.vote_count,
    }


def _eligible_places(db: Session, category: str, city: str) -> List[Place]:
    """Places in this category+city that are admin-seeded or community-approved."""
    return (db.query(Place)
              .filter(Place.category == category,
                      Place.city == city,
                      Place.status.in_(("admin", "approved")))
              .all())

def _is_open_now(hours_str: str) -> bool:
    if not hours_str:
        return False
    if "always" in hours_str.lower():
        return True
    try:
        return OpeningHours(hours_str).is_open()
    except Exception:
        return False


def _weight(place: dict, seen_place_ids: set) -> float:
    """
    Higher = more likely to be picked.

    Inputs in our crowdsourced model:
      - quality: based on vote_count
      - novelty: a small boost if the user hasn't picked this place recently
      - jitter: random tiebreaker so we don't always pick the same place first for everyone
      - open_now: multiplier to prefer currently open places (0 or 1)
    """
    quality = 3.5 + min(1.5, place.get("vote_count", 0) * 0.1)   # 3.5 → 5.0 cap
    novelty = 0.0 if place["place_id"] in seen_place_ids else 1.5
    jitter = random.uniform(0, 0.5)
    open_now = 1.0 if _is_open_now(place.get("hours", "")) else 0.0
    score = (quality + novelty + jitter) * (open_now * 0.5 + 1.0)  # 1.5x boost if open, but don't penalize closed places too much
    return score

_reason_cache: dict[tuple, str] = {}

def _generate_reason(place: dict, category: str, user_id: int, recent_names: list[str] = []) -> str:
    print(f"_generate_reason called with place_id={place['place_id']}, category={category}, user_id={user_id}, recent_names={recent_names}")
    if place.get("description"):
        return place["description"]

    template = f"A solid local {category}"

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    print(f"USE_ANTHROPIC={USE_ANTHROPIC}, api_key={'set' if api_key else 'not set'}")
    if not (USE_ANTHROPIC and api_key):
        return template

    cache_key = (place["place_id"], user_id, str(datetime.now().date()))
    if cache_key in _reason_cache:
        print(f"Using cached reason for place_id={place['place_id']} and user_id={user_id}")
        return _reason_cache[cache_key]

    try:
        print(f"Generating reason for place_id={place['place_id']} for user_id={user_id} with recent_names={recent_names}")
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)

        history_note = ""
        if recent_names:
            history_note = f"The user recently visited: {', '.join(recent_names)}. "

        messages = [{
            "role": "user",
            "content": (
                f"{history_note}Write ONE short sentence (max 18 words) telling a student "
                f"why they should visit this {category} in {place.get('city','')}: "
                f"name={place['name']}, address={place.get('address','')}, "
                f"hours={place.get('hours','')}. "
                f"No emoji. No exclamation marks. Friendly but not breathless."
            ),
        }]

        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(client.messages.create,
                               model="claude-haiku-4-5-20251001",
                               max_tokens=60,
                               messages=messages)
            msg = future.result(timeout=2.0)

        result = msg.content[0].text.strip()
        _reason_cache[cache_key] = result
        return result
    except Exception:
        return template


def _pick_for_user(db: Session, user_id: int, category: str, city: str) -> dict:
    rows = _eligible_places(db, category, city)
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No approved places for {category} in {city}. "
                   f"Suggest one with POST /places/suggest.")

    candidates = [_place_to_dict(p) for p in rows]
    seen = {
        p.place_id for p in db.query(Pick)
        .filter(Pick.user_id == user_id,
                Pick.created_at >= datetime.now(timezone.utc) - timedelta(days=7)
                ).all()
    }

    scored = sorted(candidates, key=lambda p: _weight(p, seen), reverse=True)
    chosen = scored[0]

    recent_names = [p.place_name for p in db.query(Pick)
                    .filter(Pick.user_id == user_id)
                    .order_by(Pick.created_at.desc()).limit(3).all()
                    if p.place_name]

    chosen["why"] = _generate_reason(chosen, category, user_id, recent_names)
    return chosen


def _pick_response(p: Pick, chosen: dict) -> PickResponse:
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


# ----- /pick routes ---------------------------------------------------------

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
    return _pick_response(p, chosen)


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
    return _pick_response(p, chosen)


@router.post("/pick/{pick_id}/visited")
def mark_visited(pick_id: int, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    p = db.query(Pick).filter(Pick.id == pick_id, Pick.user_id == user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pick not found")
    if p.visited_at is None:
        p.visited_at = datetime.utcnow()

    # Inline streak update — Role 3 will refactor this into gamification.py later.
    streak = db.query(Streak).filter(Streak.user_id == user.id).first()
    today = date.today()
    if not streak:
        streak = Streak(user_id=user.id, current=1, longest=1, last_visit_date=today)
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
    return {"streak_current": streak.current, "streak_longest": streak.longest}


@router.post("/pick/{pick_id}/thumbs")
def thumbs(pick_id: int, value: int,
           user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    """Crowdsourced quality signal on the pick: +1 worth it, -1 skip it."""
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
    Greedy itinerary: top place per category, ordered nearest-neighbor.
    """
    stops_raw = []
    for cat in body.categories:
        rows = _eligible_places(db, cat, body.city)
        if rows:
            best = max(rows, key=lambda p: (p.vote_count, p.id))
            stops_raw.append((cat, _place_to_dict(best)))

    if not stops_raw:
        raise HTTPException(status_code=404, detail="No places found")

    ordered = [stops_raw[0]]
    remaining = stops_raw[1:]
    while remaining:
        last = ordered[-1][1]
        remaining.sort(key=lambda x: (x[1]["lat"] - last["lat"])**2
                                     + (x[1]["lon"] - last["lon"])**2)
        ordered.append(remaining.pop(0))

    stops = [
        Stop(place_id=p["place_id"], name=p["name"], address=p.get("address", ""),
             lat=p["lat"], lon=p["lon"], category=cat)
        for cat, p in ordered
    ]
    total = 30 * len(stops) + 10 * max(0, len(stops) - 1)
    return ItineraryResponse(stops=stops, total_minutes=total)


# ----- /places routes (crowdsourced CRUD) ----------------------------------

def _place_out(p: Place) -> PlaceOut:
    return PlaceOut(
        id=p.id, name=p.name, address=p.address or "",
        lat=p.lat, lon=p.lon, category=p.category, city=p.city,
        photo_url=p.photo_url, hours=p.hours, description=p.description,
        status=p.status, vote_count=p.vote_count,
    )


@router.get("/places", response_model=List[PlaceOut])
def list_places(category: Optional[str] = None,
                city: Optional[str] = None,
                status: Optional[str] = None,
                db: Session = Depends(get_db)):
    """
    Public listing of places. Defaults to admin+approved if status omitted.
    """
    q = db.query(Place)
    if status:
        q = q.filter(Place.status == status)
    else:
        q = q.filter(Place.status.in_(("admin", "approved")))
    if category:
        q = q.filter(Place.category == category)
    if city:
        q = q.filter(Place.city == city)
    return [_place_out(p) for p in q.order_by(Place.vote_count.desc()).all()]


@router.get("/places/pending", response_model=List[PlaceOut])
def list_pending(city: Optional[str] = None,
                 db: Session = Depends(get_db)):
    """Pending submissions, anyone can see and vote."""
    q = db.query(Place).filter(Place.status == "pending")
    if city:
        q = q.filter(Place.city == city)
    return [_place_out(p) for p in q.order_by(Place.created_at.desc()).all()]


@router.get("/places/{place_id}", response_model=PlaceOut)
def get_place(place_id: int, db: Session = Depends(get_db)):
    p = db.query(Place).filter(Place.id == place_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Place not found")
    return _place_out(p)


@router.post("/places/suggest", response_model=PlaceOut)
def suggest_place(body: SuggestPlaceRequest,
                  user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """Any logged-in user can suggest a new place. Starts as 'pending'."""
    if not body.name or not body.name.strip():
        raise HTTPException(status_code=400, detail="Place name cannot be empty")
    p = Place(
        name=body.name.strip(), address=body.address or "", lat=body.lat, lon=body.lon,
        category=body.category, city=body.city,
        hours=body.hours, description=body.description, photo_url=body.photo_url,
        status="pending", submitted_by=user.id, vote_count=0,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _place_out(p)


@router.post("/places/{place_id}/vote", response_model=PlaceOut)
def vote_place(place_id: int,
               user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    """
    Upvote a pending place. One vote per user per place (enforced by uniq).
    Auto-promotes to 'approved' when vote_count >= PLACE_PROMOTION_VOTES.
    """
    p = db.query(Place).filter(Place.id == place_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Place not found")
    if p.status not in ("pending",):
        raise HTTPException(status_code=400, detail="Only pending places accept votes")

    existing = db.query(PlaceVote).filter(
        PlaceVote.place_id == place_id, PlaceVote.user_id == user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already voted")

    db.add(PlaceVote(place_id=place_id, user_id=user.id))
    p.vote_count += 1
    if p.vote_count >= PLACE_PROMOTION_VOTES:
        p.status = "approved"
    db.commit()
    db.refresh(p)
    return _place_out(p)


# ----- Admin-only -----------------------------------------------------------

@router.post("/places/{place_id}/approve", response_model=PlaceOut)
def admin_approve(place_id: int,
                  admin: User = Depends(get_admin_user),
                  db: Session = Depends(get_db)):
    p = db.query(Place).filter(Place.id == place_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Place not found")
    p.status = "approved"
    db.commit()
    db.refresh(p)
    return _place_out(p)


@router.post("/places/{place_id}/reject", response_model=PlaceOut)
def admin_reject(place_id: int,
                 admin: User = Depends(get_admin_user),
                 db: Session = Depends(get_db)):
    p = db.query(Place).filter(Place.id == place_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Place not found")
    p.status = "rejected"
    db.commit()
    db.refresh(p)
    return _place_out(p)


@router.delete("/places/{place_id}")
def admin_delete(place_id: int,
                 admin: User = Depends(get_admin_user),
                 db: Session = Depends(get_db)):
    p = db.query(Place).filter(Place.id == place_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Place not found")
    db.delete(p)
    db.commit()
    return {"deleted": place_id}
