# TikTok → Google My Maps Pipeline

## Overview

Two-phase project to extract place recommendations from saved TikTok videos and generate an importable file for Google My Maps.

**Hardware:** M1 Max MacBook Pro, 64GB RAM  
**Stack:** whisper.cpp (local transcription), Python (pipeline orchestration), yt-dlp (video download)

---

## Phase 1: Local Whisper Transcription Server

### Goal
Get whisper.cpp running as an HTTP server on localhost so the pipeline can POST audio files and get transcripts back.

### Steps for Claude Code

```
1. Clone and build whisper.cpp

   git clone https://github.com/ggerganov/whisper.cpp.git
   cd whisper.cpp
   # M1 Max has excellent Metal/CoreML support — use the default cmake build
   cmake -B build
   cmake --build build --config Release

2. Download a model
   
   # "medium" is the sweet spot for M1 Max — fast enough for batch, accurate enough 
   # for noisy TikTok audio with music/effects
   ./models/download-ggml-model.sh medium

   # If you want faster (slightly less accurate): use "small"  
   # If you want best accuracy and don't mind ~2x slower: use "large-v3"

3. Start the HTTP server

   ./build/bin/whisper-server \
     -m models/ggml-medium.bin \
     --host 127.0.0.1 \
     --port 8080

   # This exposes a POST /inference endpoint
   # Test it:
   curl http://127.0.0.1:8080/inference \
     -H "Content-Type: multipart/form-data" \
     -F file="@samples/jfk.wav" \
     -F response_format="json"

4. Verify it returns JSON with a "text" field containing the transcript
```

### Notes
- The whisper.cpp server handles WAV and other audio formats
- M1 Max should transcribe a 60-second TikTok in ~2-4 seconds with the medium model
- The server stays running in a terminal tab; the Python pipeline hits it over HTTP
- If the server binary is named differently in your build, check `build/bin/` for `server` or `whisper-server`

---

## Phase 2: TikTok-to-Maps Python Pipeline

### Goal
Python CLI tool that takes a list of TikTok URLs, extracts place names, and outputs a CSV ready to import into Google My Maps.

### Project Structure

```
tiktok-to-maps/
├── pyproject.toml          # or requirements.txt
├── config.py               # Whisper server URL, API keys
├── main.py                 # CLI entry point
├── downloader.py           # yt-dlp video/metadata download
├── transcriber.py          # Sends audio to whisper.cpp server
├── extractor.py            # Claude API to parse places from transcript
├── geocoder.py             # Google Places API to resolve locations
├── exporter.py             # Output CSV/KML for Google My Maps
└── urls.txt                # Input file — one TikTok URL per line
```

### Dependencies

```
pip install yt-dlp anthropic requests
```

- **yt-dlp** — downloads TikTok videos and extracts metadata (description, title)
- **anthropic** — Claude API for intelligent place extraction
- **requests** — HTTP calls to whisper.cpp server and Google Places API

### Module-by-Module Plan

#### `downloader.py` — Download & Extract Audio

```python
"""
Use yt-dlp to:
1. Download the TikTok video
2. Extract metadata (title, description, uploader)
3. Extract audio as WAV for whisper.cpp

Key yt-dlp options:
  - Use cookies/browser cookie extraction if TikTok blocks requests
    yt-dlp --cookies-from-browser chrome URL
  - Extract audio only to save disk:
    yt-dlp -x --audio-format wav -o "downloads/%(id)s.%(ext)s" URL
  - Also grab metadata:
    yt-dlp --write-info-json URL

Interface:
  download(url: str) -> dict with keys:
    - audio_path: str (path to .wav file)
    - description: str (video description text)
    - title: str
    - video_id: str
"""
```

#### `transcriber.py` — Send Audio to Whisper Server

```python
"""
POST the .wav file to the local whisper.cpp server.

Endpoint: POST http://127.0.0.1:8080/inference
Content-Type: multipart/form-data
Fields:
  - file: the audio file
  - response_format: "json"
  - language: "en" (optional, speeds up detection)

Returns the transcript text.

Interface:
  transcribe(audio_path: str) -> str
"""
```

#### `extractor.py` — Parse Places with Claude

```python
"""
Send the transcript + description to Claude API to extract structured place data.

Prompt strategy:
  - Provide both the TikTok description AND the audio transcript
  - Ask Claude to extract: place name, type (restaurant/bar/attraction/shop/etc),
    neighborhood or cross streets if mentioned, what was recommended about it
  - Ask Claude to be specific — "that dumpling place" should become a best guess
    like "Vanessa's Dumpling House" with a confidence note
  - Ask for JSON output

System prompt should include:
  - "You are extracting NYC restaurant and attraction recommendations from TikTok transcripts"
  - "The user is planning a trip to NYC"
  - "Return a JSON array of objects with: name, type, neighborhood, description, confidence"
  - "If the creator mentions a specific dish or activity, include that in description"

Interface:
  extract_places(transcript: str, description: str, url: str) -> list[dict]
"""
```

#### `geocoder.py` — Resolve to Coordinates

```python
"""
Take extracted place names and resolve them to lat/lng using Google Places API.

Two options:

Option A: Google Places API (Text Search)
  - Requires a Google Cloud API key with Places API enabled
  - POST to https://places.googleapis.com/v1/places:searchText
  - Query: "{place_name} NYC" 
  - Returns formatted address, lat/lng, place_id, rating, etc.
  - Cost: ~$0.032 per request (first $200/month free)

Option B: Google Maps Geocoding API (free tier)
  - Simpler but less smart about business names
  - Better as a fallback

Strategy:
  - Try Places Text Search first with the extracted name + "NYC"
  - If confidence from Claude was low, also try with neighborhood context
  - Cache results to avoid duplicate API calls

Interface:
  geocode(place_name: str, neighborhood: str = None) -> dict with:
    - lat, lng, formatted_address, place_id, name (as Google knows it)
"""
```

#### `exporter.py` — Generate Google My Maps Import File

```python
"""
Google My Maps supports CSV import with these columns:
  Name, Address, Latitude, Longitude, Description, Category

Also supports KML for richer data (icons, colors by category).

CSV approach (simplest):
  - One row per place
  - Category column lets you style layers in My Maps (Food, Drinks, Attractions, etc.)
  - Description can include the TikTok recommendation + link to original video

KML approach (fancier):
  - Group placemarks into folders by category
  - Add custom descriptions with HTML
  - Include links back to the TikTok

Interface:
  export_csv(places: list[dict], output_path: str)
  export_kml(places: list[dict], output_path: str)  # stretch goal
"""
```

#### `main.py` — CLI Orchestrator

```python
"""
CLI flow:

  python main.py --input urls.txt --output nyc_spots.csv

Pipeline per URL:
  1. downloader.download(url) -> metadata + audio file
  2. transcriber.transcribe(audio_path) -> transcript text  
  3. extractor.extract_places(transcript, description) -> list of places
  4. geocoder.geocode(place) for each place -> lat/lng
  5. Collect all places across all URLs
  6. Deduplicate (same place from multiple TikToks)
  7. exporter.export_csv(all_places, output_path)

Additional features:
  - Progress bar (tqdm) for batch processing
  - Resume support — save intermediate results to JSON so you don't re-process
  - Rate limiting for API calls
  - Error handling per-URL (skip failures, report at end)
"""
```

### Configuration Needed

```python
# config.py
WHISPER_SERVER_URL = "http://127.0.0.1:8080/inference"
ANTHROPIC_API_KEY = "sk-ant-..."  # or use ANTHROPIC_API_KEY env var
GOOGLE_PLACES_API_KEY = "..."     # or use GOOGLE_PLACES_API_KEY env var
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"  # Sonnet is plenty for extraction
```

### Google My Maps Import

Once the CSV is generated:
1. Go to https://www.google.com/maps/d/
2. Create new map → "Import" → upload the CSV
3. It'll ask which column is the location — pick Latitude/Longitude
4. Pick "Name" as the title column
5. Use "Category" to create separate layers (Food, Drinks, Attractions)
6. Color-code layers as you like

---

## Cost Estimate (for ~50 TikToks)

| Component | Cost |
|-----------|------|
| whisper.cpp | Free (local) |
| yt-dlp | Free |
| Claude API (~50 calls, Sonnet) | ~$0.50 |
| Google Places API (~75 lookups) | Free tier covers it |
| **Total** | **~$0.50** |

---

## Stretch Goals

- **Batch mode with saved TikToks:** If you can export your saved/liked TikToks list, auto-feed all URLs
- **Confidence scoring:** Flag low-confidence extractions for manual review
- **Duplicate detection:** Merge entries when multiple TikToks mention the same spot, combine descriptions
- **Auto-categorize by meal:** Breakfast/lunch/dinner/late-night based on context
- **Neighborhood clustering:** Group nearby spots to help with day planning