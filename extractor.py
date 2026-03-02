import json
import anthropic
import config

SYSTEM_PROMPT = """You are extracting restaurant and attraction recommendations from TikTok transcripts and descriptions. The user is planning a trip to NYC.

Return a JSON array of objects. Each object should have:
- "name": The specific place name (be as specific as possible — if they say "that dumpling place on Eldridge", guess the actual name like "Vanessa's Dumpling House")
- "type": One of: restaurant, bar, cafe, bakery, pizza, attraction, shop, hotel, park
- "neighborhood": The NYC neighborhood if mentioned (e.g. "East Village", "Williamsburg")
- "description": What was recommended — specific dishes, activities, tips mentioned
- "confidence": "high" if the place was named explicitly, "medium" if you're making an educated guess, "low" if very uncertain

Rules:
- Only extract real, specific places — not generic advice like "eat pizza"
- If the creator mentions a specific dish, include it in the description
- If multiple places are mentioned, return all of them
- If no specific places are identifiable, return an empty array []
- Return ONLY the JSON array, no other text"""


def extract_places(transcript: str, description: str, url: str) -> list[dict]:
    """Use Claude to extract place recommendations from transcript + description."""
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    user_message = f"""TikTok URL: {url}

Video description:
{description}

Audio transcript:
{transcript}

Extract all place recommendations from this TikTok."""

    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    text = response.content[0].text.strip()

    # Parse JSON from response — handle markdown code fences
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    places = json.loads(text)

    food_types = {"restaurant", "bar", "cafe", "bakery", "pizza"}
    for place in places:
        place["source_url"] = url
        place["layer"] = "Food & Drink" if place.get("type", "").lower() in food_types else "Attraction"

    return places
