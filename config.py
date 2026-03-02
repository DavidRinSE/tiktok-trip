import os
from dotenv import load_dotenv

load_dotenv()

WHISPER_SERVER_URL = os.environ.get("WHISPER_SERVER_URL", "http://127.0.0.1:8080/inference")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")

DOWNLOADS_DIR = "downloads"
CACHE_FILE = "cache.json"
