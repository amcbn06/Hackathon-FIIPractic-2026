"""
The heart of OnePick: turn a (category, city) into exactly one place.

Instead of returning a list to scroll through, we weight the eligible places
and sample one. Weighting blends crowdsourced quality, novelty (places the user
hasn't seen recently), whether it's open right now, and a little jitter so two
users asking at the same time don't always get the same answer.
"""

from __future__ import annotations

import random

from sqlalchemy.orm import Session

from backend.models import ELIGIBLE_STATUSES, Pick, Place

try:  # optional dependency; degrade gracefully if unavailable
    from opening_hours import OpeningHours
except Exception:  # pragma: no cover
    OpeningHours = None


def _is_open_now(hours: str | None) -> bool:
    if not hours:
        return False
    low = hours.lower()
    if "24/7" in low or "always" in low or "00:00-24:00" in low:
        return True
    if OpeningHours is None:
        return False
    try:
        return OpeningHours(hours).is_open()
    except Exception:
        return False


def _weight(place: Place, seen_ids: set[str]) -> float:
    quality = 3.5 + min(1.5, (place.vote_count or 0) * 0.1)  # 3.5 -> 5.0
    novelty = 0.0 if str(place.id) in seen_ids else 1.5
    open_bonus = 0.8 if _is_open_now(place.hours) else 0.0
    jitter = random.uniform(0, 0.5)
    return quality + novelty + open_bonus + jitter


def eligible_places(db: Session, category: str, city: str) -> list[Place]:
    """Places in this category+city that are admin-seeded or approved.

    Falls back to any city for the category if none exist in the given city.
    """
    rows = (
        db.query(Place)
        .filter(
            Place.category == category,
            Place.city == city,
            Place.status.in_(ELIGIBLE_STATUSES),
        )
        .all()
    )
    if rows:
        return rows
    return (
        db.query(Place)
        .filter(Place.category == category, Place.status.in_(ELIGIBLE_STATUSES))
        .all()
    )


def choose_place(db: Session, user_id: int, category: str, city: str) -> Place | None:
    """Pick one place using weighted random sampling. None if nothing fits."""
    places = eligible_places(db, category, city)
    if not places:
        return None

    recent = (
        db.query(Pick.place_id)
        .filter(Pick.user_id == user_id)
        .order_by(Pick.created_at.desc())
        .limit(10)
        .all()
    )
    seen_ids = {r[0] for r in recent if r[0]}

    weights = [_weight(p, seen_ids) for p in places]
    return random.choices(places, weights=weights, k=1)[0]
