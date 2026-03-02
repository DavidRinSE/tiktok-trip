import json
import os
import shutil
import subprocess
import sys
import config


def _ytdlp_path() -> str:
    """Find yt-dlp, preferring the venv's copy."""
    venv_bin = os.path.join(os.path.dirname(sys.executable), "yt-dlp")
    if os.path.isfile(venv_bin):
        return venv_bin
    found = shutil.which("yt-dlp")
    if found:
        return found
    raise FileNotFoundError("yt-dlp not found — install it with: pip install yt-dlp")


def download(url: str) -> dict:
    """Download TikTok video, extract audio as WAV and metadata.

    Returns dict with keys: audio_path, description, title, video_id
    """
    os.makedirs(config.DOWNLOADS_DIR, exist_ok=True)

    # First, extract metadata without downloading
    meta_cmd = [
        _ytdlp_path(),
        "--dump-json",
        "--no-download",
        "--cookies-from-browser", "chrome",
        url,
    ]
    result = subprocess.run(meta_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp metadata extraction failed for {url}: {result.stderr}")

    info = json.loads(result.stdout)
    video_id = info.get("id", "unknown")
    title = info.get("title", "")
    description = info.get("description", "")

    # Download audio as WAV
    audio_path = os.path.join(config.DOWNLOADS_DIR, f"{video_id}.wav")

    if not os.path.exists(audio_path):
        dl_cmd = [
            _ytdlp_path(),
            "-x", "--audio-format", "wav",
            "-o", os.path.join(config.DOWNLOADS_DIR, f"{video_id}.%(ext)s"),
            "--cookies-from-browser", "chrome",
            url,
        ]
        result = subprocess.run(dl_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"yt-dlp audio download failed for {url}: {result.stderr}")

    return {
        "audio_path": audio_path,
        "description": description,
        "title": title,
        "video_id": video_id,
    }
