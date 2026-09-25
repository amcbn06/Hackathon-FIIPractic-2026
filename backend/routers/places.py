"""Picks, places catalogue (crowdsourced), and cities."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.auth import get_admin_user, get_current_user
from backend.config import settings
from backend.database import get_db
from backend.models import (
    ELIGIBLE_STATUSES,
    PLACE_APPROVED,
    PLACE_PENDING,
    PLACE_REJECTED,
    GroupCheckin,
    Group,
    Pick,
    Place,
    PlaceVote,
    User,
)
from backend.schemas import (
    PickRequest,
    PickResponse,
    PlaceOut,
    SuggestPlaceRequest,
)
from backend.services import gamification, recommend

router = APIRouter(tags=["places"])


# --- Serialization helpers ------------------------------------------------


def _place_out(p: Place) -> PlaceOut:
    return PlaceOut(
        id=p.id,
        name=p.name,
        address=p.address or "",
        lat=p.lat,
        lon=p.lon,
        category=p.category,
        city=p.city,
        photo_url=p.photo_url,
        hours=p.hours,
        description=p.description,
        status=p.status,
        vote_count=p.vote_count,
    )


def _pick_response(pick: Pick, place: Place) -> PickResponse:
    return PickResponse(
        pick_id=pick.id,
        place_id=str(place.id),
        name=place.name,
        address=place.address or "",
        lat=place.lat,
        lon=place.lon,
        category=place.category,
        city=place.city,
        why=pick.why or place.description or f"A solid local {place.category}.",
        rating=float(place.vote_count or 0),
        photo_url=place.photo_url,
        hours=place.hours,
        visited=pick.visited_at is not None,
    )


# --- Picking --------------------------------------------------------------


@router.post("/pick", response_model=PickResponse)
def create_pick(
    body: PickRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    place = recommend.choose_place(db, user.id, body.category, body.city)
    if not place:
        raise HTTPException(
            status_code=404,
            detail=f"No place found for {body.category} in {body.city}.",
        )
    pick = Pick(
        user_id=user.id,
        group_id=body.group_id,
        place_id=str(place.id),
        place_name=place.name,
        category=body.category,
        city=body.city,
        why=place.description or f"A solid local {body.category}.",
    )
    db.add(pick)
    db.commit()
    db.refresh(pick)
    return _pick_response(pick, place)


@router.post("/pick/{pick_id}/reroll", response_model=PickResponse)
def reroll(
    pick_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pick = db.query(Pick).filter(Pick.id == pick_id, Pick.user_id == user.id).first()
    if not pick:
        raise HTTPException(status_code=404, detail="Pick not found")

    today_rerolls = (
        db.query(Pick)
        .filter(
            Pick.user_id == user.id,
            Pick.created_at >= datetime.combine(date.today(), datetime.min.time()),
            Pick.reroll_count > 0,
        )
        .count()
    )
    if today_rerolls >= settings.daily_reroll_limit:
        raise HTTPException(status_code=429, detail="Daily reroll limit reached")

    place = recommend.choose_place(db, user.id, pick.category, pick.city)
    if not place:
        raise HTTPException(status_code=404, detail="Nothing else to suggest")

    pick.place_id = str(place.id)
    pick.place_name = place.name
    pick.why = place.description or f"A solid local {pick.category}."
    pick.reroll_count += 1
    db.commit()
    db.refresh(pick)
    return _pick_response(pick, place)


@router.post("/pick/{pick_id}/visited")
def mark_visited(
    pick_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pick = db.query(Pick).filter(Pick.id == pick_id).first()
    if not pick:
        raise HTTPException(status_code=404, detail="Pick not found")

    if pick.group_id:
        group = db.query(Group).filter(Group.id == pick.group_id).first()
        total_members = len(group.members) if group else 1
        existing = (
            db.query(GroupCheckin)
            .filter_by(pick_id=pick.id, user_id=user.id)
            .first()
        )
        if not existing:
            db.add(GroupCheckin(pick_id=pick.id, user_id=user.id))
            db.commit()
        checkins = db.query(GroupCheckin).filter_by(pick_id=pick.id).count()
        if checkins >= total_members and pick.visited_at is None:
            pick.visited_at = datetime.utcnow()
            db.commit()
    elif pick.visited_at is None:
        pick.visited_at = datetime.utcnow()
        db.commit()

    streak = gamification.increment_streak(db, user.id)
    return {"streak_current": streak.current, "streak_longest": streak.longest}


@router.post("/pick/{pick_id}/thumbs")
def thumbs(
    pick_id: int,
    value: int = Query(..., ge=-1, le=1),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pick = db.query(Pick).filter(Pick.id == pick_id, Pick.user_id == user.id).first()
    if not pick:
        raise HTTPException(status_code=404, detail="Pick not found")
    pick.thumbs = value
    db.commit()
    return {"thumbs": value}


# --- Places catalogue -----------------------------------------------------


@router.get("/places", response_model=list[PlaceOut])
def list_places(
    category: Optional[str] = None,
    city: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Place)
    q = q.filter(Place.status == status) if status else q.filter(
        Place.status.in_(ELIGIBLE_STATUSES)
    )
    if category:
        q = q.filter(Place.category == category)
    if city:
        q = q.filter(Place.city == city)
    return [_place_out(p) for p in q.order_by(Place.vote_count.desc()).all()]


@router.get("/places/pending", response_model=list[PlaceOut])
def list_pending(city: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Place).filter(Place.status == PLACE_PENDING)
    if city:
        q = q.filter(Place.city == city)
    return [_place_out(p) for p in q.order_by(Place.created_at.desc()).all()]


@router.get("/cities")
def cities(db: Session = Depends(get_db)):
    rows = (
        db.query(Place.city)
        .filter(Place.status.in_(ELIGIBLE_STATUSES))
        .distinct()
        .all()
    )
    found = sorted({r[0] for r in rows if r[0]})
    return found or ["Iași", "București", "Cluj-Napoca", "Timișoara"]


@router.get("/categories")
def categories(city: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Place.category).filter(Place.status.in_(ELIGIBLE_STATUSES))
    if city:
        q = q.filter(Place.city == city)
    rows = q.distinct().all()
    return sorted({r[0] for r in rows if r[0]})


@router.get("/places/{place_id}", response_model=PlaceOut)
def get_place(place_id: int, db: Session = Depends(get_db)):
    p = db.query(Place).filter(Place.id == place_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Place not found")
    return _place_out(p)


@router.post("/places/suggest", response_model=PlaceOut)
def suggest_place(
    body: SuggestPlaceRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Place name cannot be empty")
    p = Place(
        name=body.name.strip(),
        address=body.address or "",
        lat=body.lat,
        lon=body.lon,
        category=body.category,
        city=body.city,
        hours=body.hours,
        description=body.description,
        photo_url=body.photo_url,
        status=PLACE_PENDING,
        submitted_by=user.id,
        vote_count=0,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _place_out(p)


@router.post("/places/{place_id}/vote", response_model=PlaceOut)
def vote_place(
    place_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = db.query(Place).filter(Place.id == place_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Place not found")
    if p.status != PLACE_PENDING:
        raise HTTPException(status_code=400, detail="Only pending places accept votes")
    if (
        db.query(PlaceVote)
        .filter(PlaceVote.place_id == place_id, PlaceVote.user_id == user.id)
        .first()
    ):
        raise HTTPException(status_code=400, detail="Already voted")

    db.add(PlaceVote(place_id=place_id, user_id=user.id))
    p.vote_count += 1
    if p.vote_count >= settings.place_promotion_votes:
        p.status = PLACE_APPROVED
    db.commit()
    db.refresh(p)
    return _place_out(p)


# --- Admin ----------------------------------------------------------------


@router.post("/places/{place_id}/approve", response_model=PlaceOut)
def approve(
    place_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    p = db.query(Place).filter(Place.id == place_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Place not found")
    p.status = PLACE_APPROVED
    db.commit()
    db.refresh(p)
    return _place_out(p)


@router.post("/places/{place_id}/reject", response_model=PlaceOut)
def reject(
    place_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    p = db.query(Place).filter(Place.id == place_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Place not found")
    p.status = PLACE_REJECTED
    db.commit()
    db.refresh(p)
    return _place_out(p)


@router.delete("/places/{place_id}")
def delete_place(
    place_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    p = db.query(Place).filter(Place.id == place_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Place not found")
    db.delete(p)
    db.commit()
    return {"deleted": place_id}
