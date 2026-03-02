import requests
import config


def transcribe(audio_path: str) -> str:
    """Send a WAV file to the local whisper.cpp server and return the transcript."""
    with open(audio_path, "rb") as f:
        response = requests.post(
            config.WHISPER_SERVER_URL,
            files={"file": (audio_path, f, "audio/wav")},
            data={"response_format": "json", "language": "en"},
            timeout=120,
        )

    response.raise_for_status()
    data = response.json()

    # whisper.cpp server returns {"text": "..."} or similar
    if isinstance(data, dict):
        return data.get("text", "")
    return str(data)
