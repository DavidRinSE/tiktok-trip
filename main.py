#!/usr/bin/env python3
"""CLI tool to extract place recommendations from TikTok videos and export to a Mapbox map."""

import argparse
import json
import math
import os
import subprocess
import sys

from tqdm import tqdm

import config
from downloader import download
from transcriber import transcribe
from extractor import extract_places
from geocoder import geocode
from exporter import export_geojson, load_geojson


def load_cache() -> dict:
    if os.path.exists(config.CACHE_FILE):
        with open(config.CACHE_FILE) as f:
            return json.load(f)
    return {}


def save_cache(cache: dict):
    with open(config.CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def deduplicate(places: list[dict]) -> list[dict]:
    """Deduplicate places by Google place_id or name."""
    seen = {}
    for place in places:
        key = place.get("place_id") or place.get("google_name", place.get("name", "")).lower()
        if key not in seen:
            seen[key] = place
        else:
            # Merge descriptions from multiple TikToks
            existing = seen[key]
            if place.get("source_url") != existing.get("source_url"):
                existing["description"] = existing.get("description", "") + " | Also mentioned in: " + place.get("source_url", "")
    return list(seen.values())


def _haversine_m(lat1, lon1, lat2, lon2):
    """Return distance in metres between two lat/lng points."""
    R = 6_371_000
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def merge_with_existing(new_places: list[dict], geojson_path: str) -> list[dict]:
    """Load existing GeoJSON features and merge new places, deduplicating by name + proximity."""
    existing_features = load_geojson(geojson_path)
    if not existing_features:
        return new_places

    # Convert existing GeoJSON features back to place dicts
    existing_places = []
    for feat in existing_features:
        props = feat.get("properties", {})
        coords = feat.get("geometry", {}).get("coordinates", [None, None])
        place = {
            "google_name": props.get("name", ""),
            "name": props.get("name", ""),
            "emoji": props.get("emoji", "📍"),
            "type": props.get("category", "").lower(),
            "neighborhood": props.get("neighborhood", ""),
            "description": props.get("description", ""),
            "source_url": props.get("tiktok_url", ""),
            "formatted_address": props.get("address", ""),
            "rating": props.get("rating"),
            "lng": coords[0],
            "lat": coords[1],
        }
        existing_places.append(place)

    # Merge: check each new place against existing by name + ~50m proximity
    for new_place in new_places:
        is_dup = False
        new_name = (new_place.get("google_name") or new_place.get("name", "")).lower()
        new_lat = new_place.get("lat")
        new_lng = new_place.get("lng")

        for existing in existing_places:
            ex_name = (existing.get("google_name") or existing.get("name", "")).lower()
            ex_lat = existing.get("lat")
            ex_lng = existing.get("lng")

            if new_name == ex_name:
                # Same name — check proximity if coords available
                if new_lat and new_lng and ex_lat and ex_lng:
                    dist = _haversine_m(new_lat, new_lng, ex_lat, ex_lng)
                    if dist < 50:
                        # Merge description
                        if new_place.get("source_url") != existing.get("source_url"):
                            existing["description"] = existing.get("description", "") + " | Also mentioned in: " + new_place.get("source_url", "")
                        is_dup = True
                        break
                else:
                    # No coords to compare — treat same name as duplicate
                    if new_place.get("source_url") != existing.get("source_url"):
                        existing["description"] = existing.get("description", "") + " | Also mentioned in: " + new_place.get("source_url", "")
                    is_dup = True
                    break

        if not is_dup:
            existing_places.append(new_place)

    return existing_places


def process_url(url: str, cache: dict) -> list[dict]:
    """Run the full pipeline for a single TikTok URL."""
    url = url.strip()
    if not url:
        return []

    # Check cache
    if url in cache:
        print(f"  Using cached results for {url}")
        return cache[url]

    # Step 1: Download
    print(f"  Downloading...")
    meta = download(url)

    # Step 2: Transcribe
    print(f"  Transcribing...")
    transcript = transcribe(meta["audio_path"])

    # Step 3: Extract places with Claude
    print(f"  Extracting places...")
    places = extract_places(transcript, meta["description"], url)

    if not places:
        print(f"  No places found")
        cache[url] = []
        return []

    print(f"  Found {len(places)} place(s): {', '.join(p['name'] for p in places)}")

    # Step 4: Geocode each place
    for place in places:
        print(f"  Geocoding: {place['name']}...")
        geo = geocode(place["name"], place.get("neighborhood"))
        if geo:
            place.update(geo)
        else:
            print(f"    Could not geocode '{place['name']}'")

    cache[url] = places
    return places


def deploy(geojson_path: str):
    """Auto-commit and push the GeoJSON data."""
    try:
        subprocess.run(["git", "add", geojson_path], check=True)
        subprocess.run(["git", "commit", "-m", "Update places data"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("Deployed: committed and pushed to origin/main")
    except subprocess.CalledProcessError as e:
        print(f"Deploy failed: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Extract places from TikTok videos for an interactive map")
    parser.add_argument("--input", "-i", default="urls.txt", help="File with TikTok URLs, one per line")
    parser.add_argument("--output", "-o", default="docs/places.geojson", help="Output GeoJSON path (default: docs/places.geojson)")
    parser.add_argument("--no-cache", action="store_true", help="Ignore cached results")
    parser.add_argument("--append", action="store_true", help="Merge new places into existing GeoJSON, deduplicating by name + proximity")
    parser.add_argument("--deploy", action="store_true", help="After export, git add/commit/push the GeoJSON to origin/main")
    args = parser.parse_args()

    # Validate config
    if not config.ANTHROPIC_API_KEY:
        print("Error: Set ANTHROPIC_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)
    if not config.GOOGLE_PLACES_API_KEY:
        print("Error: Set GOOGLE_PLACES_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)

    # Read URLs
    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' not found", file=sys.stderr)
        sys.exit(1)

    with open(args.input) as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    print(f"Processing {len(urls)} TikTok URL(s)...\n")

    cache = {} if args.no_cache else load_cache()
    all_places = []
    errors = []

    for url in tqdm(urls, desc="TikToks"):
        try:
            places = process_url(url, cache)
            all_places.extend(places)
            save_cache(cache)  # Save after each URL for resume support
        except Exception as e:
            errors.append((url, str(e)))
            print(f"  ERROR: {e}")

    # Deduplicate within this run
    all_places = deduplicate(all_places)

    # Merge with existing data if --append
    if args.append:
        all_places = merge_with_existing(all_places, args.output)
        print(f"Merged with existing data from {args.output}")

    # Export
    output_path = export_geojson(all_places, args.output)
    geocoded = sum(1 for p in all_places if p.get("lat") or p.get("lng"))
    print(f"\nExported {len(all_places)} place(s) ({geocoded} geocoded) to {output_path}")

    if errors:
        print(f"\n{len(errors)} URL(s) failed:")
        for url, err in errors:
            print(f"  {url}: {err}")

    # Deploy if requested
    if args.deploy:
        deploy(args.output)


if __name__ == "__main__":
    main()
