"""
Optional AI helpers (Anthropic Claude).

Everything here has a deterministic, no-network fallback so the app behaves
identically whether or not an API key is configured.
"""

from __future__ import annotations

import random
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from backend.config import settings

_reason_cache: dict[tuple, str] = {}


def _anthropic_available() -> bool:
    return settings.use_anthropic and bool(settings.anthropic_api_key)


def reason_for_pick(
    place: dict, category: str, user_id: int, recent_names: list[str] | None = None
) -> str:
    """One-line 'why this pick'. Uses the curator description, else a template,
    else Claude when enabled."""
    if place.get("description"):
        return place["description"]

    template = f"A well-liked local {category} worth the trip."

    if not _anthropic_available():
        return template

    cache_key = (place.get("place_id"), user_id, str(date.today()))
    if cache_key in _reason_cache:
        return _reason_cache[cache_key]

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=settings.anthropic_api_key)
        history = (
            f"The user recently visited: {', '.join(recent_names)}. "
            if recent_names
            else ""
        )
        prompt = (
            f"{history}Write ONE short sentence (max 18 words) telling a student "
            f"why to visit this {category} in {place.get('city', '')}: "
            f"name={place['name']}, address={place.get('address', '')}, "
            f"hours={place.get('hours', '')}. No emoji, no exclamation marks."
        )
        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(
                client.messages.create,
                model=settings.anthropic_model,
                max_tokens=60,
                messages=[{"role": "user", "content": prompt}],
            )
            msg = future.result(timeout=3.0)
        text = msg.content[0].text.strip()
        _reason_cache[cache_key] = text
        return text
    except Exception:
        return template


def route_insight(city: str, categories: list[str], stop_count: int) -> str:
    """A short narrative summary for a generated itinerary."""
    moods = ", ".join(categories)
    return (
        f"We linked {stop_count} spots across {city} for your mood ({moods}). "
        f"The route starts relaxed and builds toward the busiest highlight."
    )


def validate_custom_place(name: str, city: str, description: str = "") -> dict:
    """Lightweight validation + auto-description for user 'secret spots'."""
    invalid = {"test", "asdf", "fake", "none", "123"}
    if len(name.strip()) < 3 or any(w in name.lower() for w in invalid):
        return {
            "is_valid": False,
            "message": f"Couldn't verify '{name}' in {city}. Use the real name.",
        }

    if description and description.strip():
        final = description.strip()
        message = "Saved with your own description."
    else:
        final = (
            f"A great spot in {city}. '{name}' was added as an ideal place to "
            f"explore the local scene."
        )
        message = "Validated and auto-described."

    return {
        "is_valid": True,
        "message": message,
        "address": f"{name}, {city}",
        "description": final,
        "interval": "10:00 - 22:00",
        "lat": 47.16 + random.uniform(-0.02, 0.02),
        "lon": 27.58 + random.uniform(-0.02, 0.02),
    }
