# TikTok to Google Maps

Extracts restaurant and attraction recommendations from TikTok videos and exports them as CSV files you can import into Google My Maps.

**Pipeline:** TikTok URL → yt-dlp (download audio) → whisper.cpp (transcribe) → Claude (extract places) → Google Places API (geocode) → CSV

## Prerequisites

- Python 3.10+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- A local [whisper.cpp](https://github.com/ggerganov/whisper.cpp) server
- An [Anthropic API key](https://console.anthropic.com/)
- A [Google Cloud API key](https://console.cloud.google.com/) with the Places API (New) enabled

## Setup

### 1. Clone and install dependencies

```bash
git clone <repo-url> && cd tiktok-trip
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

Options:

```
-i, --input FILE    Input file with TikTok URLs (default: urls.txt)
-o, --output FILE   Output CSV base name (default: nyc_spots.csv)
--no-cache          Ignore cached results and re-process everything
```

This produces two CSV files: `nyc_spots_food.csv` and `nyc_spots_attractions.csv`.

Results are cached in `cache.json` so re-running skips already-processed URLs.

## Importing into Google My Maps

1. Go to [mymaps.google.com](https://mymaps.google.com) and click **"+ Create a new map"**
2. Name your map (click "Untitled map" in the top left)

**Import the Food layer:**

3. Click **Import** under the default layer
4. Upload `nyc_spots_food.csv`
5. Select **Latitude** and **Longitude** as position columns
6. Select **Name** as the marker title column
7. Click **Finish**, then rename the layer to "Food"

**Import the Attractions layer:**

8. Click **Add layer**
9. Click **Import** on the new layer
10. Upload `nyc_spots_attractions.csv`
11. Same column selections as above — **Latitude**/**Longitude** for position, **Name** for title
12. Click **Finish**, then rename the layer to "Attractions"

**Style the pins (optional):**

Click the paint bucket icon under each layer to give Food and Attractions different colors. Each pin's description includes the TikTok summary, Google rating, and source link.
