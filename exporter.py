import csv
import os


def export_csv(places: list[dict], output_base: str) -> tuple[str, str]:
    """Write places to two CSV files (food + attractions) for Google My Maps import.

    Returns the two file paths created.
    """
    base, ext = os.path.splitext(output_base)
    if not ext:
        ext = ".csv"
    food_path = f"{base}_food{ext}"
    attractions_path = f"{base}_attractions{ext}"

    food = [p for p in places if p.get("layer") == "Food & Drink"]
    attractions = [p for p in places if p.get("layer") != "Food & Drink"]

    _write_csv(food, food_path)
    _write_csv(attractions, attractions_path)

    return food_path, attractions_path


def _write_csv(places: list[dict], path: str):
    fieldnames = ["Name", "Address", "Latitude", "Longitude", "Description", "Category", "Source"]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for place in places:
            writer.writerow({
                "Name": place.get("google_name", place.get("name", "")),
                "Address": place.get("formatted_address", ""),
                "Latitude": place.get("lat", ""),
                "Longitude": place.get("lng", ""),
                "Description": _build_description(place),
                "Category": place.get("type", "").capitalize(),
                "Source": place.get("source_url", ""),
            })


def _build_description(place: dict) -> str:
    parts = []
    if place.get("description"):
        parts.append(place["description"])
    elif place.get("type"):
        parts.append(place["type"].capitalize())
    if place.get("confidence") and place["confidence"] != "high":
        parts.append(f"[confidence: {place['confidence']}]")
    if place.get("rating"):
        parts.append(f"Google rating: {place['rating']}")
    if place.get("source_url"):
        parts.append(f"From: {place['source_url']}")
    return "\n".join(parts)
