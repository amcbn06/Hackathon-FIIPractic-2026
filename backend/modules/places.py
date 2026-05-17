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
from backend.modules import gamification
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user, get_admin_user
from backend.db import User, Pick, Streak, Place, PlaceVote, get_db,Group, GroupInvite, GroupCheckin,GroupMember,ItineraryStop,Itinerary

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
    
class SaveItineraryRequest(BaseModel):
    city: str
    stops: list


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
    open_bonus = 0.8 if _is_open_now(place.get("hours", "")) else 0.0
    return quality + novelty + jitter + open_bonus

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
    """Alege o locație din baza de date pentru un utilizator singur."""
    
    # 1. Căutăm doar locațiile din DB care se potrivesc
    places = db.query(Place).filter(
        Place.category == category,
        Place.city == city,
        Place.status.in_(("admin", "approved"))
    ).all()

    # 2. Fallback la oraș
    if not places:
        places = db.query(Place).filter(
            Place.category == category,
            Place.status.in_(("admin", "approved"))
        ).all()

    # 3. Eroare curată dacă tabelul este gol pe această categorie
    if not places:
        raise HTTPException(
            status_code=404,
            detail=f"Nu există nicio locație în baza de date pentru {category} în {city}."
        )

    # 4. Alegem aleatoriu DOAR din ce ai tu în JSON/Baza de date
    chosen_place = random.choice(places)

    # 5. Formăm dicționarul exact cum îl așteaptă restul aplicației
    return {
        "place_id": str(chosen_place.id),
        "name": chosen_place.name,
        "address": chosen_place.address or "",
        "lat": chosen_place.lat,
        "lon": chosen_place.lon,
        "category": chosen_place.category,
        "city": chosen_place.city,
        "photo_url": chosen_place.photo_url,
        "hours": chosen_place.hours,
        "why": chosen_place.description or f"O alegere excelentă pentru {category}!",
        "rating": getattr(chosen_place, "vote_count", 0.0)
    }

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
def mark_visited(pick_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(Pick).filter(Pick.id == pick_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pick not found")

    if p.group_id:
        # LOGICA PENTRU GRUP
        group = db.query(Group).filter(Group.id == p.group_id).first()
        total_members = len(group.members) if group else 1
        
        # Verificăm dacă userul a dat deja check-in
        existing_checkin = db.query(GroupCheckin).filter_by(pick_id=p.id, user_id=user.id).first()
        if not existing_checkin:
            db.add(GroupCheckin(pick_id=p.id, user_id=user.id))
            db.commit()
            
        # Verificăm câți au dat check-in în total
        checkin_count = db.query(GroupCheckin).filter_by(pick_id=p.id).count()
        
        # Dacă toți au dat check-in, abia acum marcăm locația ca fiind vizitată oficial!
        if checkin_count >= total_members and p.visited_at is None:
            p.visited_at = datetime.utcnow()
            db.commit()
    else:
        # LOGICA PENTRU SOLO
        if p.visited_at is None:
            p.visited_at = datetime.utcnow()
            db.commit()

    streak = gamification.increment_streak(db, user.id)
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

@router.get("/me/advanced_history")
def advanced_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returnează datele separate perfect pentru To Do și History, inclusiv Itinerariile!"""
    
    # 1. SOLO PICKS
    solo_picks = db.query(Pick).filter(Pick.user_id == user.id, Pick.group_id == None).order_by(Pick.created_at.desc()).all()
    todo_solo, hist_solo = [], []
    for p in solo_picks:
        item = {"pick_id": p.id, "place_name": p.place_name, "category": p.category, "city": p.city}
        if p.visited_at: hist_solo.append(item)
        else: todo_solo.append(item)

    # 2. GROUP PICKS
    user_groups = db.query(GroupMember).filter(GroupMember.user_id == user.id).all()
    group_ids = [g.group_id for g in user_groups]
    group_picks = db.query(Pick).filter(Pick.group_id.in_(group_ids)).order_by(Pick.created_at.desc()).all() if group_ids else []
    todo_group, hist_group = [], []

    for p in group_picks:
        group = db.query(Group).filter(Group.id == p.group_id).first()
        total_members = len(group.members) if group else 1
        checkins = db.query(GroupCheckin).filter(GroupCheckin.pick_id == p.id).all()
        checked_in_ids = [c.user_id for c in checkins]
        
        item = {
            "pick_id": p.id, 
            "place_name": p.place_name, 
            "category": p.category,
            "group_name": group.name if group else "Unknown Group",
            "total_members": total_members,
            "checked_in_count": len(checked_in_ids),
            "i_checked_in": user.id in checked_in_ids
        }
        if p.visited_at: hist_group.append(item)
        else: todo_group.append(item)

    # 3. ITINERARIES (Traseele noi!)
    user_itineraries = db.query(Itinerary).filter(Itinerary.user_id == user.id).all()
    todo_itin, hist_itin = [], []

    for itin in user_itineraries:
        stops = db.query(ItineraryStop).filter(ItineraryStop.itinerary_id == itin.id).all()
        total_stops = len(stops)
        visited_stops = sum(1 for s in stops if s.visited_at)
        stops_detail = [{"stop_id": s.id, "place_name": s.place_name, "category": s.category, "visited": bool(s.visited_at)} for s in stops]

        itin_data = {
            "itinerary_id": itin.id,
            "city": itin.city,
            "created_at": itin.created_at.strftime("%d %b %Y") if itin.created_at else "Recent",
            "total_stops": total_stops,
            "visited_stops": visited_stops,
            "stops": stops_detail
        }

        # Dacă e completat, merge la History. Dacă nu, stă la To-Do!
        if itin.completed_at or (total_stops > 0 and visited_stops == total_stops):
            hist_itin.append(itin_data)
        else:
            todo_itin.append(itin_data)

    # 4. TRIMITEREA CĂTRE FRONTEND
    return {
        "todo": {"solo": todo_solo, "group": todo_group, "itineraries": todo_itin},
        "history": {"solo": hist_solo, "group": hist_group, "itineraries": hist_itin}
    }
    
@router.post("/itinerary/save")
def save_itinerary(body: SaveItineraryRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Salvează un traseu nou generat direct în Tracker-ul tău."""
    new_itin = Itinerary(user_id=user.id, city=body.city)
    db.add(new_itin)
    db.commit()
    db.refresh(new_itin)

    for stop in body.stops:
        new_stop = ItineraryStop(
            itinerary_id=new_itin.id,
            place_id=stop.get("place_id", "unknown"),
            place_name=stop.get("name", "Unknown Place"),
            category=stop.get("category", "place")
        )
        db.add(new_stop)
    db.commit()
    return {"detail": "Itinerary saved"}

@router.post("/itinerary/stop/{stop_id}/visited")
def mark_itinerary_stop(stop_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Bifează o locație din traseu. Dacă e ultima, traseul devine Completat."""
    stop = db.query(ItineraryStop).filter(ItineraryStop.id == stop_id).first()
    if stop and not stop.visited_at:
        stop.visited_at = datetime.utcnow()
        db.commit()

        # Verificăm dacă mai sunt locații nebifate în traseul ăsta
        unvisited = db.query(ItineraryStop).filter(
            ItineraryStop.itinerary_id == stop.itinerary_id,
            ItineraryStop.visited_at == None
        ).count()

        if unvisited == 0:
            itin = db.query(Itinerary).filter(Itinerary.id == stop.itinerary_id).first()
            itin.completed_at = datetime.utcnow()
            db.commit()
    return {"detail": "Stop marked visited"}