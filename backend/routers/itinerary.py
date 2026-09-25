"""Multi-stop itineraries: generate, save, and tick off stops."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import Itinerary, ItineraryStop, Place, User
from backend.schemas import (
    ItineraryRequest,
    ItineraryResponse,
    SaveItineraryRequest,
    Stop,
)
from backend.services import ai, recommend

router = APIRouter(tags=["itinerary"])


def _order_nearest_neighbor(items: list[tuple[str, Place]]) -> list[tuple[str, Place]]:
    """Greedy nearest-neighbour ordering starting from the first stop."""
    if not items:
        return []
    ordered = [items[0]]
    remaining = items[1:]
    while remaining:
        last = ordered[-1][1]
        remaining.sort(
            key=lambda x: (x[1].lat - last.lat) ** 2 + (x[1].lon - last.lon) ** 2
        )
        ordered.append(remaining.pop(0))
    return ordered


@router.post("/itinerary", response_model=ItineraryResponse)
def generate_itinerary(
    body: ItineraryRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    raw: list[tuple[str, Place]] = []
    for cat in body.categories:
        rows = recommend.eligible_places(db, cat, body.city)
        if rows:
            best = max(rows, key=lambda p: (p.vote_count, p.id))
            raw.append((cat, best))

    if not raw:
        raise HTTPException(status_code=404, detail="No places found for those vibes")

    ordered = _order_nearest_neighbor(raw)
    stops = [
        Stop(
            place_id=str(p.id),
            name=p.name,
            address=p.address or "",
            lat=p.lat,
            lon=p.lon,
            category=cat,
        )
        for cat, p in ordered
    ]
    total = 30 * len(stops) + 10 * max(0, len(stops) - 1)
    insight = ai.route_insight(body.city, body.categories, len(stops))
    return ItineraryResponse(stops=stops, total_minutes=total, insight=insight)


@router.post("/itinerary/save")
def save_itinerary(
    body: SaveItineraryRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    itin = Itinerary(user_id=user.id, city=body.city)
    db.add(itin)
    db.flush()
    for i, stop in enumerate(body.stops):
        db.add(
            ItineraryStop(
                itinerary_id=itin.id,
                place_id=str(stop.get("place_id", "unknown")),
                place_name=stop.get("name", "Unknown place"),
                category=stop.get("category", "place"),
                lat=stop.get("lat"),
                lon=stop.get("lon"),
                position=i,
            )
        )
    db.commit()
    return {"itinerary_id": itin.id}


@router.post("/itinerary/stop/{stop_id}/visited")
def mark_stop(
    stop_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stop = db.query(ItineraryStop).filter(ItineraryStop.id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Stop not found")
    if not stop.visited_at:
        stop.visited_at = datetime.utcnow()
        db.commit()
        remaining = (
            db.query(ItineraryStop)
            .filter(
                ItineraryStop.itinerary_id == stop.itinerary_id,
                ItineraryStop.visited_at.is_(None),
            )
            .count()
        )
        if remaining == 0:
            itin = (
                db.query(Itinerary)
                .filter(Itinerary.id == stop.itinerary_id)
                .first()
            )
            if itin:
                itin.completed_at = datetime.utcnow()
                db.commit()
    return {"detail": "Stop marked visited"}
