import time

import requests
import config

_cache: dict[str, dict] = {}


def geocode(place_name: str, neighborhood: str | None = None) -> dict | None:
    """Resolve a place name to lat/lng using Google Places Text Search API.

    Returns dict with: lat, lng, formatted_address, place_id, google_name
    Returns None if no result found.
    """
    query = f"{place_name} NYC"
    if neighborhood:
        query = f"{place_name} {neighborhood} NYC"

    cache_key = query.lower()
    if cache_key in _cache:
        return _cache[cache_key]

    # Use the new Places API (v1)
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": config.GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.id,places.rating",
    }
    body = {"textQuery": query}

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=body, headers=headers, timeout=15)
            if response.status_code in (403, 429) or response.status_code >= 500:
                response.raise_for_status()
            response.raise_for_status()
            break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
            if isinstance(e, requests.exceptions.HTTPError) and response.status_code < 500 and response.status_code not in (403, 429):
                raise
            if attempt < max_retries - 1:
                wait = 2 ** attempt  # 1s, 2s, 4s
                print(f"  ⚠ Google Places API error ({e}), retrying in {wait}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise
    data = response.json()

    places = data.get("places", [])
    if not places:
        _cache[cache_key] = None
        return None

    top = places[0]
    location = top.get("location", {})
    result = {
        "lat": location.get("latitude"),
        "lng": location.get("longitude"),
        "formatted_address": top.get("formattedAddress", ""),
        "place_id": top.get("id", ""),
        "google_name": top.get("displayName", {}).get("text", place_name),
        "rating": top.get("rating"),
    }

    _cache[cache_key] = result
    return result
