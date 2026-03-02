import json
import os


def export_geojson(places: list[dict], output_path: str = "docs/places.geojson") -> str:
    """Write places to a GeoJSON file for the Mapbox static site.

    Returns the file path created.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    features = []
    for place in places:
        lat = place.get("lat")
        lng = place.get("lng")
        if lat is None or lng is None:
            continue

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lng, lat],  # GeoJSON is [longitude, latitude]
            },
            "properties": {
                "name": place.get("google_name", place.get("name", "")),
                "emoji": place.get("emoji", "📍"),
                "category": place.get("type", "").capitalize(),
                "neighborhood": place.get("neighborhood", ""),
                "description": place.get("description", ""),
                "tiktok_url": place.get("source_url", ""),
                "address": place.get("formatted_address", ""),
                "rating": place.get("rating"),
            },
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2, ensure_ascii=False)

    return output_path


def load_geojson(path: str) -> list[dict]:
    """Load existing GeoJSON and return list of features."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("features", [])
