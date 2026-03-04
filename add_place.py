#!/usr/bin/env python3
"""Quick geocoding lookup for adding places to the map.

Usage:
    python3 add_place.py "Joe's Pizza West Village NYC"

Outputs JSON with resolved place details to stdout.
"""

import json
import sys

import requests
import config


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 add_place.py <search query>", file=sys.stderr)
        sys.exit(1)

    query = sys.argv[1]

    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": config.GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.id,places.rating",
    }
    response = requests.post(url, json={"textQuery": query}, headers=headers, timeout=15)
    response.raise_for_status()
    data = response.json()

    places = data.get("places", [])
    if not places:
        print(json.dumps({"error": f"No results found for: {query}"}))
        sys.exit(1)

    top = places[0]
    location = top.get("location", {})
    output = {
        "google_name": top.get("displayName", {}).get("text", query),
        "lat": location.get("latitude"),
        "lng": location.get("longitude"),
        "address": top.get("formattedAddress", ""),
        "place_id": top.get("id", ""),
        "rating": top.get("rating"),
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
