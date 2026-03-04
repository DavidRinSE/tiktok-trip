# Add to Map

Quickly add a place to the trip map from a casual description.

## Trigger
User says things like:
- "add Woo Woo dive bar"
- "add that pizza place on Bleecker"
- "put Joe's Pizza on the map"
- Any variation of wanting to add a place to the map

## Steps

1. **Geocode the place** — Run the lookup tool with the user's query. Add "NYC" to the query if the user didn't specify a location:
   ```
   venv/bin/python3 add_place.py "<query>"
   ```
   Parse the JSON output to get `google_name`, `lat`, `lng`, `address`, `rating`, `place_id`.

2. **Check for duplicates** — Read `docs/places.geojson` and check if a feature with the same name (case-insensitive) already exists. If it does, tell the user and ask if they want to update or skip.

3. **Infer details** using the geocoded result + your own knowledge + any context the user gave:
   - **category**: One of: Restaurant, Bar, Cafe, Bakery, Pizza, Attraction, Shop, Hotel, Park
   - **emoji**: Follow these conventions from the project:
     - Restaurant → 🍽️
     - Bar → 🍸
     - Cafe/coffee → ☕
     - Bakery → 🧁
     - Pizza → 🍕
     - Attraction → 🎭
     - Shop → 🛍️
     - Hotel → 🏨
     - Park → 🌳
     - Use a more specific emoji when appropriate (e.g. 🍜 for noodles, 🍕 for pizza, 🌮 for tacos)
   - **neighborhood**: Infer from the address (e.g. "East Village", "Williamsburg")
   - **description**: Combine what the user said with your knowledge of the place. Include specific dishes, vibes, or tips if known.

4. **Show the user what will be added** — Display the full feature entry and ask for confirmation. Example:
   ```
   Adding to map:
   📍 Joe's Pizza — 🍕 Pizza
   📫 7 Carmine St, New York, NY 10014
   📝 Classic NYC slice joint, known for their cheese slice
   ⭐ 4.4

   Add this? (or tell me what to change)
   ```

5. **Edit the GeoJSON** — On confirmation, edit `docs/places.geojson` to append a new feature before the closing `]` of the features array. Use this format:
   ```json
   {
     "type": "Feature",
     "geometry": {
       "type": "Point",
       "coordinates": [<lng>, <lat>]
     },
     "properties": {
       "name": "<google_name or user-provided name>",
       "emoji": "<emoji>",
       "category": "<category>",
       "neighborhood": "<neighborhood>",
       "description": "<description>",
       "tiktok_url": null,
       "address": "<address>",
       "rating": <rating or null>
     }
   }
   ```
   Note: coordinates are `[longitude, latitude]` (GeoJSON standard).

6. **Confirm** — Tell the user the place was added to the map.
