"""
Geoapify Places API wrapper.

Owner: Role 2.

Free tier: https://myprojects.geoapify.com (no credit card required).
Docs: https://apidocs.geoapify.com/docs/places/

Falls back to a small mock dataset if GEOAPIFY_API_KEY is not set, so the rest
of the team isn't blocked while Role 2 wires up the real integration.
"""

import os
import json
from typing import List, Dict, Optional

import requests

GEOAPIFY_KEY = os.getenv("GEOAPIFY_API_KEY", "")
PLACES_URL = "https://api.geoapify.com/v2/places"
GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"

# Map our user-facing categories to Geoapify category strings
CATEGORY_MAP = {
    "park":       "leisure.park",
    "museum":     "entertainment.museum",
    "cafe":       "catering.cafe",
    "bar":        "catering.bar",
    "restaurant": "catering.restaurant",
    "viewpoint":  "tourism.sights.viewpoint",
}


def geocode_city(city: str) -> Optional[Dict[str, float]]:
    """Return {"lat": ..., "lon": ...} for a city name, or None on failure."""
    if not GEOAPIFY_KEY:
        # Iași centroid as a sane default for the demo
        return {"lat": 47.1585, "lon": 27.6014}
    try:
        r = requests.get(
            GEOCODE_URL,
            params={"text": city, "format": "json", "apiKey": GEOAPIFY_KEY},
            timeout=5,
        )
        r.raise_for_status()
        results = r.json().get("results", [])
        if not results:
            return None
        return {"lat": results[0]["lat"], "lon": results[0]["lon"]}
    except requests.RequestException:
        return None


def search_places(category: str, city: str, radius_m: int = 3000,
                  limit: int = 20) -> List[Dict]:
    """
    Search for POIs of a given category near a city. Returns a list of dicts:
        {place_id, name, address, lat, lon, rating, photo_url, hours, raw}

    Falls back to MOCK_PLACES if no API key is configured.
    """
    if not GEOAPIFY_KEY:
        return [p for p in MOCK_PLACES if p["category"] == category][:limit]

    coords = geocode_city(city)
    if not coords:
        return []

    cat = CATEGORY_MAP.get(category, category)
    try:
        r = requests.get(
            PLACES_URL,
            params={
                "categories": cat,
                "filter": f"circle:{coords['lon']},{coords['lat']},{radius_m}",
                "bias":   f"proximity:{coords['lon']},{coords['lat']}",
                "limit":  limit,
                "apiKey": GEOAPIFY_KEY,
            },
            timeout=5,
        )
        r.raise_for_status()
        features = r.json().get("features", [])
    except requests.RequestException:
        return []

    out = []
    for f in features:
        props = f.get("properties", {})
        out.append({
            "place_id": props.get("place_id"),
            "name": props.get("name") or props.get("address_line1") or "Unnamed place",
            "address": props.get("formatted", ""),
            "lat": props.get("lat"),
            "lon": props.get("lon"),
            "rating": None,            # Geoapify doesn't return ratings on free tier
            "photo_url": None,
            "hours": props.get("opening_hours"),
            "raw": json.dumps(props),
        })
    return out


# ----- Mock data so the team isn't blocked --------------------------------

MOCK_PLACES = [
    {
        "place_id": "mock-cafe-1",
        "name": "Mock Café Central",
        "category": "cafe",
        "address": "Strada Lăpușneanu 14, Iași",
        "lat": 47.1700, "lon": 27.5780,
        "rating": 4.5, "photo_url": None,
        "hours": "Mo-Su 08:00-22:00", "raw": "{}",
    },
    {
        "place_id": "mock-park-1",
        "name": "Mock Copou Park",
        "category": "park",
        "address": "Bd. Carol I, Iași",
        "lat": 47.1849, "lon": 27.5727,
        "rating": 4.7, "photo_url": None,
        "hours": "24/7", "raw": "{}",
    },
    {
        "place_id": "mock-museum-1",
        "name": "Mock Palace Museum",
        "category": "museum",
        "address": "Piața Ștefan cel Mare, Iași",
        "lat": 47.1572, "lon": 27.5879,
        "rating": 4.6, "photo_url": None,
        "hours": "Tu-Su 10:00-17:00", "raw": "{}",
    },
]
