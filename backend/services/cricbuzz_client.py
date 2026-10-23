import os
from pathlib import Path
from typing import Any, Optional

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

REQUEST_TIMEOUT = 20


class CricbuzzAPIError(Exception):
    """Raised when a Cricbuzz API request fails."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code


def _get_config(name: str) -> str:
    """Read a configuration value from the environment."""
    return os.getenv(name, "").strip()


def _request_json(
    path: str,
    params: Optional[dict] = None,
) -> Any:
    api_key = _get_config("CRICBUZZ_API_KEY")
    api_host = _get_config("CRICBUZZ_API_HOST")

    missing = []
    if not api_key:
        missing.append("CRICBUZZ_API_KEY")
    if not api_host:
        missing.append("CRICBUZZ_API_HOST")
    if missing:
        raise CricbuzzAPIError(
            "Cricbuzz API configuration is missing: "
            + ", ".join(missing)
            + ". Check these values in the project .env file."
        )

    if not isinstance(path, str) or not path.strip():
        raise CricbuzzAPIError("Cricbuzz endpoint path cannot be empty.")

    path = path.strip()
    if not path.startswith("/"):
        path = "/" + path

    # The RapidAPI host must be a hostname, not a URL or endpoint path.
    api_host = api_host.removeprefix("https://").removeprefix("http://").strip("/")
    if not api_host or "/" in api_host:
        raise CricbuzzAPIError(
            "CRICBUZZ_API_HOST must be a hostname only, without a scheme or path."
        )

    url = f"https://{api_host}{path}"
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": api_host,
        "Accept": "application/json",
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.exceptions.Timeout as error:
        raise CricbuzzAPIError(
            f"Cricbuzz request timed out after {REQUEST_TIMEOUT} seconds."
        ) from error
    except requests.exceptions.RequestException as error:
        # Do not include request headers or the request object in diagnostics.
        raise CricbuzzAPIError(
            f"Network error while contacting Cricbuzz ({type(error).__name__})."
        ) from error

    if not response.ok:
        status_code = response.status_code
        if status_code in (401, 403):
            message = (
                f"RapidAPI returned HTTP {status_code}. Check the API key, "
                "subscription access, and configured host."
            )
        elif status_code == 404:
            message = (
                "RapidAPI returned HTTP 404. Check the endpoint path and "
                "external match/player ID."
            )
        elif status_code == 429:
            message = (
                "RapidAPI returned HTTP 429. Check your quota and rate limits."
            )
        elif status_code >= 500:
            message = (
                f"The Cricbuzz/RapidAPI provider returned HTTP {status_code}. "
                "The provider may be temporarily unavailable."
            )
        else:
            message = f"Cricbuzz/RapidAPI returned HTTP {status_code}."

        # Short response preview helps debugging; credentials are never added.
        body_preview = " ".join(response.text.split())[:300]
        if body_preview:
            message += f" Provider response: {body_preview}"
        raise CricbuzzAPIError(message, status_code=status_code)

    try:
        return response.json()
    except ValueError as error:
        raise CricbuzzAPIError(
            "Cricbuzz returned a successful HTTP response that was not valid JSON."
        ) from error


def _validate_id(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise CricbuzzAPIError(f"{label} must be a positive integer.")

    try:
        result = int(value)
    except (TypeError, ValueError) as error:
        raise CricbuzzAPIError(
            f"{label} must be a positive integer."
        ) from error

    if result <= 0:
        raise CricbuzzAPIError(f"{label} must be a positive integer.")

    return result


def _require_object(data: Any, label: str) -> dict:
    if not isinstance(data, dict):
        raise CricbuzzAPIError(
            f"Cricbuzz returned an unexpected {label} response format."
        )
    return data


def get_live_matches() -> dict:
    path = _get_config("CRICBUZZ_LIVE_MATCHES_PATH")
    if not path:
        raise CricbuzzAPIError(
            "Missing CRICBUZZ_LIVE_MATCHES_PATH in the project .env file."
        )
    return _require_object(_request_json(path), "live-matches")


def get_match_scorecard(match_id: int) -> dict:
    match_id = _validate_id(match_id, "Match ID")
    data = _request_json(f"/mcenter/v1/{match_id}/scard")
    return _require_object(data, "scorecard")


def search_players(player_name: str) -> dict:
    """Search for players by name."""
    if not isinstance(player_name, str) or not player_name.strip():
        raise CricbuzzAPIError("Enter a player name to search.")
    data = _request_json(
        "/stats/v1/player/search",
        params={"plrN": player_name.strip()},
    )
    return _require_object(data, "player-search")


def get_player_info(player_id: int) -> dict:
    """Retrieve a player's profile."""
    player_id = _validate_id(player_id, "Player ID")
    data = _request_json(f"/stats/v1/player/{player_id}")
    return _require_object(data, "player-info")


def get_player_career(player_id: int) -> dict:
    """Retrieve a player's career timeline."""
    player_id = _validate_id(player_id, "Player ID")
    data = _request_json(f"/stats/v1/player/{player_id}/career")
    return _require_object(data, "player-career")


def get_player_batting(
    player_id: int,
    series_id: Optional[int] = None,
) -> dict:
    """Retrieve a player's batting statistics."""
    player_id = _validate_id(player_id, "Player ID")
    params = None
    if series_id is not None:
        series_id = _validate_id(series_id, "Series ID")
        params = {"seriesId": series_id}
    data = _request_json(
        f"/stats/v1/player/{player_id}/batting",
        params=params,
    )
    return _require_object(data, "batting-statistics")


def get_player_bowling(
    player_id: int,
    series_id: Optional[int] = None,
) -> dict:
    """Retrieve a player's bowling statistics."""
    player_id = _validate_id(player_id, "Player ID")
    params = None
    if series_id is not None:
        series_id = _validate_id(series_id, "Series ID")
        params = {"seriesId": series_id}
    data = _request_json(
        f"/stats/v1/player/{player_id}/bowling",
        params=params,
    )
    return _require_object(data, "bowling-statistics")
