# Upgrade Plan: Static Mapbox Site on GitHub Pages

## Overview

Upgrade the tiktok-to-maps pipeline to replace CSV export with a mobile-first static Mapbox site. The pipeline outputs GeoJSON, the site renders it with emoji markers and tap-to-expand info cards. Hosted on GitHub Pages for free, accessible from any phone.

---

## Architecture Change

```
BEFORE:
  TikTok URLs → download → transcribe → extract → geocode → CSV file → manual My Maps import

AFTER:
  TikTok URLs → download → transcribe → extract → geocode → GeoJSON → static site → GitHub Pages
```

The repo becomes both the pipeline AND the site:

```
tiktok-to-maps/
├── pipeline/
│   ├── main.py
│   ├── downloader.py
│   ├── transcriber.py
│   ├── extractor.py        # Updated: now also picks emoji per place
│   ├── geocoder.py
│   └── config.py
├── docs/                    # GitHub Pages serves from /docs
│   ├── index.html           # Single-file Mapbox app
│   └── places.geojson       # Pipeline output goes here
├── urls.txt
└── README.md
```

GitHub Pages serves the `docs/` folder. The pipeline writes `places.geojson` directly into `docs/`.

---

## Part 1: Update `extractor.py` — Add Emoji Selection

### What Changes

The Claude API prompt already extracts place name, type, neighborhood, and description. Update it to also return an emoji for each place.

### Updated Prompt Strategy

Add to the system prompt:

```
For each place, also pick a single emoji that best represents it at a glance.
Use these conventions:
  - 🍕 pizza, 🍣 sushi, 🍜 noodles/ramen, 🌮 tacos/mexican
  - 🍔 burgers, 🥐 bakery/pastry, ☕ coffee, 🍦 ice cream/dessert
  - 🍸 cocktail bar, 🍺 beer/brewery, 🍷 wine bar
  - 🥩 steakhouse, 🍝 italian/pasta, 🥟 dumplings
  - 🍽️ general restaurant (if nothing more specific fits)
  - 🎭 theater/show, 🏛️ museum, 🌳 park, 🛍️ shopping
  - 📸 photo spot/viewpoint, 🎵 music venue, 🎨 gallery
  - ⭐ general attraction/experience
Pick the most specific emoji possible. Only one emoji per place.
```

### Updated Output Schema

```json
{
  "name": "Vanessa's Dumpling House",
  "type": "restaurant",
  "emoji": "🥟",
  "neighborhood": "Chinatown",
  "description": "Creator recommended the chive and pork fried dumplings, $3 for 4",
  "confidence": "high"
}
```

---

## Part 2: Update `exporter.py` → Replace CSV with GeoJSON

### What Changes

Remove `export_csv()`. Replace with `export_geojson()` that writes a GeoJSON FeatureCollection to `docs/places.geojson`.

### GeoJSON Format

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-73.9957, 40.7158]
      },
      "properties": {
        "name": "Vanessa's Dumpling House",
        "emoji": "🥟",
        "category": "restaurant",
        "neighborhood": "Chinatown",
        "description": "Chive and pork fried dumplings — $3 for 4. Cash only.",
        "tiktok_url": "https://www.tiktok.com/@user/video/1234567890",
        "address": "118A Eldridge St, New York, NY 10002",
        "rating": 4.3
      }
    }
  ]
}
```

### Implementation Notes

- `coordinates` is `[longitude, latitude]` — GeoJSON uses lng/lat order, NOT lat/lng
- Include the original TikTok URL so users can tap through to the video
- Include the Google-resolved address and rating from the geocoder
- Write to `docs/places.geojson` relative to the project root

---

## Part 3: Build `docs/index.html` — Static Mapbox Site

### Requirements

Single HTML file. No build step. Everything inline — HTML, CSS, JS. Loads Mapbox GL JS from CDN and fetches `places.geojson` from the same directory.

### Mapbox Setup

- Use Mapbox GL JS v3 from CDN
- Mapbox access token embedded in the HTML (public token, restricted to your GitHub Pages domain)
- Default style: `mapbox://styles/mapbox/streets-v12` (or `light-v11` for cleaner look)
- Initial view centered on NYC: `center: [-73.98, 40.75], zoom: 12`

### Emoji Markers

Use custom HTML markers, NOT symbol layers. This avoids needing to manage image sprites.

```javascript
// For each feature in the GeoJSON:
const el = document.createElement('div');
el.className = 'emoji-marker';
el.textContent = feature.properties.emoji;
// Style: font-size ~28px, cursor pointer, with a subtle drop shadow

new mapboxgl.Marker({ element: el })
  .setLngLat(feature.geometry.coordinates)
  .setPopup(popup)
  .addTo(map);
```

### Popup Cards (Tap-to-Expand Info)

On marker tap, show a Mapbox Popup with:

```html
<div class="popup-card">
  <h3>🥟 Vanessa's Dumpling House</h3>
  <p class="neighborhood">Chinatown</p>
  <p class="description">Chive and pork fried dumplings — $3 for 4. Cash only.</p>
  <p class="address">118A Eldridge St, New York, NY 10002</p>
  <a href="https://tiktok.com/..." target="_blank">📱 Watch the TikTok</a>
  <a href="https://www.google.com/maps/dir/?api=1&destination=40.7158,-73.9957" target="_blank">🧭 Directions</a>
</div>
```

Key details:
- Include a Google Maps directions deeplink — this opens turn-by-turn on mobile
- TikTok link opens the original video
- Style the popup for mobile: max-width 280px, readable font sizes, fat tap targets on links

### Category Filter Bar

Fixed bar at the top of the screen (or bottom for better mobile thumb reach):

```
[All] [🍽️ Food] [🍸 Drinks] [🎭 Attractions] [🛍️ Shopping]
```

Implementation:
- Derive categories from the data (group by `category` field)
- Toggle markers visible/hidden based on active filter
- Active filter gets a highlight style
- "All" shows everything
- Store markers in a JS array, loop and call `marker.remove()` / `marker.addTo(map)` to toggle

### Mobile-First CSS

```
- Full viewport map: width 100vw, height 100dvh (use dvh not vh for mobile browser chrome)
- Filter bar: sticky, horizontal scroll if many categories, no wrapping
- Popup cards: max-width 280px, 16px font, 44px minimum tap targets on links
- Emoji markers: 28-32px font size with slight text-shadow for visibility
- Safe area insets for notched phones: padding env(safe-area-inset-*)
- Prevent map zoom on double-tap of UI elements
```

### Offline Consideration

Mapbox tiles require internet, but the GeoJSON is bundled. If you want basic offline support later, you could add a service worker, but skip this for v1.

---

## Part 4: Update `main.py` — Add Auto-Deploy Step

### Updated CLI Flow

```
python main.py --input urls.txt

# Pipeline runs all steps, then:
# 1. Writes docs/places.geojson
# 2. Optionally auto-commits and pushes to GitHub

python main.py --input urls.txt --deploy
# Same as above but also runs:
#   git add docs/places.geojson
#   git commit -m "Update places data"
#   git push origin main
```

### Append Mode

Important: support appending new places to an existing GeoJSON file, not just overwriting.

```
python main.py --input new_urls.txt --append
```

- Load existing `docs/places.geojson`
- Deduplicate by place name + coordinates (fuzzy match within ~50m)
- Merge descriptions if same place from multiple TikToks
- Write updated file

---

## Part 5: GitHub Pages Setup

### One-Time Setup (Manual or Claude Code)

1. Create the GitHub repo (if not already):
   ```
   gh repo create tiktok-to-maps --public --source=. --push
   ```

2. Enable GitHub Pages:
   - Go to repo Settings → Pages
   - Source: "Deploy from a branch"
   - Branch: `main`, folder: `/docs`
   - Save

3. Restrict Mapbox token:
   - Go to Mapbox account → Access tokens
   - Create a new public token
   - Under "URL restrictions" add: `yourusername.github.io`
   - Paste token into `docs/index.html`

4. Site will be live at: `https://yourusername.github.io/tiktok-to-maps/`

### Bookmark to Home Screen

On iOS Safari:
- Navigate to the site
- Share → Add to Home Screen
- Now it launches like an app with no browser chrome

---

## Part 6: Nice-to-Haves (After v1 Works)

- **Cluster nearby markers** at low zoom levels using Mapbox's built-in clustering, with cluster count badge
- **"Near me" button** that uses device GPS and sorts/highlights places within walking distance
- **Day planner view** — sidebar or bottom sheet that lets you drag places into an ordered itinerary for the day, draws a walking route
- **Search/filter by text** — search box to filter by name or description
- **Multiple trips** — support separate GeoJSON files per trip, toggle between them
- **PWA manifest** — add a manifest.json so the home screen bookmark gets a custom icon and splash screen

---

## Summary of File Changes

| File | Action | What |
|------|--------|------|
| `pipeline/extractor.py` | **Modify** | Add emoji field to Claude prompt and output schema |
| `pipeline/exporter.py` | **Modify** | Replace `export_csv` with `export_geojson`, output to `docs/` |
| `pipeline/main.py` | **Modify** | Add `--deploy` and `--append` flags, git push step |
| `docs/index.html` | **Create** | Single-file Mapbox static site |
| `docs/places.geojson` | **Generated** | Pipeline output, committed to repo |