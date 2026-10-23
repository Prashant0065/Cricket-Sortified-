from backend.services.cricbuzz_client import (
    get_live_matches,
    CricbuzzAPIError,
)
import json

try:
    data = get_live_matches()

    print("Cricbuzz API connection successful!")
    print("Top-level keys:", list(data.keys()) if isinstance(data, dict) else "Response is not a dictionary")
    print("Response preview:")
    print(json.dumps(data, indent=2)[:5000])

except CricbuzzAPIError as error:
    print("Cricbuzz API error:", error)
