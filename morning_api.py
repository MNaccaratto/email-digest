import urllib.request
import json


def get_morning_briefing() -> dict:
    briefing = {"quote": "", "author": ""}

    # Fetch Daily Quote
    try:
        req = urllib.request.Request(
            "https://zenquotes.io/api/today", headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data and isinstance(data, list) and "q" in data[0]:
                briefing["quote"] = data[0]["q"]
                briefing["author"] = data[0]["a"]
    except Exception:
        pass

    return briefing
