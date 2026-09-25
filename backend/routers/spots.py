"""Custom personal "secret spots" + the AI validation/route endpoints."""

from __future__ import annotations

import random

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import CustomLocation, Place, User
from backend.schemas import (
    CustomLocationOut,
    CustomLocationRequest,
    ItineraryRequest,
)
from backend.services import ai

router = APIRouter(tags=["spots"])


@router.post("/custom-locations", response_model=CustomLocationOut)
def add_custom_location(
    body: CustomLocationRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Validate a personal spot (AI-assisted) and store it."""
    result = ai.validate_custom_place(body.name, body.city, body.description or "")
    if not result["is_valid"]:
        raise HTTPException(status_code=400, detail=result["message"])

    loc = CustomLocation(
        user_id=user.id,
        name=body.name.strip(),
        description=result["description"],
        address=result.get("address"),
        interval=result.get("interval"),
        rating=body.rating,
        lat=result.get("lat"),
        lon=result.get("lon"),
        ai_generated=not bool(body.description and body.description.strip()),
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return CustomLocationOut(
        id=loc.id,
        name=loc.name,
        description=loc.description,
        address=loc.address,
        interval=loc.interval,
        rating=loc.rating,
        ai_generated=loc.ai_generated,
        created_at=loc.created_at.strftime("%d %b %Y") if loc.created_at else None,
    )


@router.get("/custom-locations", response_model=list[CustomLocationOut])
def my_custom_locations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    locs = (
        db.query(CustomLocation)
        .filter(CustomLocation.user_id == user.id)
        .order_by(CustomLocation.created_at.desc())
        .all()
    )
    return [
        CustomLocationOut(
            id=l.id,
            name=l.name,
            description=l.description,
            address=l.address,
            interval=l.interval,
            rating=l.rating,
            ai_generated=l.ai_generated,
            created_at=l.created_at.strftime("%d %b %Y") if l.created_at else None,
        )
        for l in locs
    ]


@router.delete("/custom-locations/{loc_id}")
def delete_custom_location(
    loc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    loc = (
        db.query(CustomLocation)
        .filter(CustomLocation.id == loc_id, CustomLocation.user_id == user.id)
        .first()
    )
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    db.delete(loc)
    db.commit()
    return {"deleted": loc_id}


@router.post("/ai/smart-route")
def smart_route(
    body: ItineraryRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI-flavoured itinerary: one real place per category from the DB."""
    places = (
        db.query(Place)
        .filter(Place.city.ilike(body.city), Place.category.in_(body.categories))
        .all()
    )
    stops = []
    for cat in body.categories:
        matching = [p for p in places if p.category == cat]
        if matching:
            p = random.choice(matching)
            stops.append(
                {
                    "place_id": str(p.id),
                    "name": p.name,
                    "category": p.category,
                    "lat": p.lat,
                    "lon": p.lon,
                    "address": p.address or "",
                }
            )
    if not stops:
        raise HTTPException(
            status_code=404,
            detail=f"No places in {body.city} for: {', '.join(body.categories)}",
        )
    return {
        "city": body.city,
        "total_minutes": len(stops) * 45 + 30,
        "insight": ai.route_insight(body.city, body.categories, len(stops)),
        "stops": stops,
    }
