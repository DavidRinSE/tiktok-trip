# TikTok Trip Map

Turn TikTok travel recommendations into your own interactive map. Drop in TikTok URLs, run the pipeline, and get a mobile-friendly Mapbox site with emoji markers, category filters, and directions — hosted free on GitHub Pages.

Fork this repo, add your TikTok URLs, and you'll have a shareable map of every spot in minutes.

**Pipeline:** TikTok URL → yt-dlp (download audio) → whisper.cpp (transcribe) → Claude (extract places + emoji) → Google Places API (geocode) → GeoJSON → Mapbox static site

## Prerequisites

- Python 3.10+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- A local [whisper.cpp](https://github.com/ggerganov/whisper.cpp) server
- An [Anthropic API key](https://console.anthropic.com/)
- A [Google Cloud API key](https://console.cloud.google.com/) with the Places API (New) enabled
- A [Mapbox access token](https://account.mapbox.com/) (free tier works fine)

## Setup

### 1. Fork and clone

Fork this repo on GitHub, then:

```bash
git clone <your-fork-url> && cd tiktok-trip
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Set up whisper.cpp

Clone and build whisper.cpp, then download a model:

```bash
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp
cmake -B build
cmake --build build --config Release
```

Download a model (the `base.en` model is a good tradeoff between speed and quality):

```bash
./models/download-ggml-model.sh base.en
```

Start the server:

```bash
./build/bin/whisper-server -m models/ggml-base.en.bin --port 8080
```

Leave this running in a separate terminal. The app connects to `http://127.0.0.1:8080/inference` by default.

### 3. Enable the Google Places API (New)

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or select an existing one)
3. Go to **APIs & Services → Library**
4. Search for **"Places API (New)"** — make sure you enable the **New** version, not the legacy "Places API"
5. Click **Enable**
6. Go to **APIs & Services → Credentials**
7. Click **Create Credentials → API Key**
8. Copy the key for the next step

### 4. Environment variables

Create a `.env` file in the project root:

```bash
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_PLACES_API_KEY=AIza...
```

Optional variables:

```bash
WHISPER_SERVER_URL=http://127.0.0.1:8080/inference  # default
CLAUDE_MODEL=claude-sonnet-4-5-20250929              # default
```

### 5. Add your Mapbox token

Open `docs/index.html` and replace `YOUR_MAPBOX_TOKEN` with your token from [account.mapbox.com](https://account.mapbox.com/).

### 6. Enable GitHub Pages

In your fork's repo settings, go to **Pages** and set the source to deploy from the `main` branch, `/docs` folder.

## Usage

Add TikTok URLs to `urls.txt` (one per line, `#` comments are supported):

```
# NYC food videos
https://www.tiktok.com/t/ZThngDdgr/
https://www.tiktok.com/t/ZThngb1r9/
```

Run the pipeline:

```bash
python3 main.py
```

This generates `docs/places.geojson` which powers the map at `docs/index.html`.

### Options

```
-i, --input FILE    Input file with TikTok URLs (default: urls.txt)
-o, --output FILE   Output GeoJSON path (default: docs/places.geojson)
--no-cache          Ignore cached results and re-process everything
--append            Merge new places into existing GeoJSON (deduplicates by name + proximity)
--deploy            Auto-commit and push the GeoJSON to origin/main after export
```

### Adding more spots later

Use `--append` to add new TikTok URLs without losing your existing places:

```bash
python3 main.py --append
```

To update and publish in one step:

```bash
python3 main.py --append --deploy
```

Results are cached in `cache.json` so re-running skips already-processed URLs.
