#!/usr/bin/env python3
"""CLI tool to extract place recommendations from TikTok videos and export to Google My Maps."""

import argparse
import json
import os
import sys

from tqdm import tqdm

import config
from downloader import download
from transcriber import transcribe
from extractor import extract_places
from geocoder import geocode
from exporter import export_csv


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


def main():
    parser = argparse.ArgumentParser(description="Extract places from TikTok videos for Google My Maps")
    parser.add_argument("--input", "-i", default="urls.txt", help="File with TikTok URLs, one per line")
    parser.add_argument("--output", "-o", default="nyc_spots.csv", help="Output CSV base name (produces _food.csv and _attractions.csv)")
    parser.add_argument("--no-cache", action="store_true", help="Ignore cached results")
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

    # Deduplicate
    all_places = deduplicate(all_places)

    # Export
    food_path, attractions_path = export_csv(all_places, args.output)
    food_count = sum(1 for p in all_places if p.get("layer") == "Food & Drink")
    attr_count = len(all_places) - food_count
    print(f"\nExported {len(all_places)} place(s):")
    print(f"  {food_count} food spot(s) → {food_path}")
    print(f"  {attr_count} attraction(s) → {attractions_path}")

    if errors:
        print(f"\n{len(errors)} URL(s) failed:")
        for url, err in errors:
            print(f"  {url}: {err}")


if __name__ == "__main__":
    main()
