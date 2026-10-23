
import os

import requests
import streamlit as st


API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

REQUEST_TIMEOUT = 15


class BackendAPIError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


def api_request(method, endpoint, token=None, payload=None, params=None):
    url = f"{API_BASE_URL}/{endpoint.lstrip('/')}"
    headers = {}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=payload,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.exceptions.Timeout as error:
        raise BackendAPIError(
            "The backend took too long to respond. Please try again."
        ) from error
    except requests.exceptions.ConnectionError as error:
        raise BackendAPIError(
            "Cannot connect to the backend. Make sure FastAPI is running."
        ) from error
    except requests.exceptions.RequestException as error:
        raise BackendAPIError(
            "A network error occurred while contacting the backend."
        ) from error

    try:
        data = response.json()
    except ValueError:
        data = {}

    if not response.ok:
        detail = data.get("detail", "The request failed.")

        if isinstance(detail, list):
            detail = "; ".join(
                str(item.get("msg", item))
                if isinstance(item, dict)
                else str(item)
                for item in detail
            )

        error = BackendAPIError(
            f"HTTP {response.status_code}: {detail}",
            status_code=response.status_code,
        )
        raise error

    return data


def send_registration_otp(email):
    return api_request(
        "POST",
        "/auth/send-otp",
        payload={"email": email.strip().lower()},
    )


def resend_registration_otp(email):
    return api_request(
        "POST",
        "/auth/resend-otp",
        payload={"email": email.strip().lower()},
    )


def verify_email_otp(email, otp):
    return api_request(
        "POST",
        "/auth/verify-otp",
        payload={
            "email": email.strip().lower(),
            "otp": otp.strip(),
        },
    )


def complete_registration(email, username, password, confirm_password):
    return api_request(
        "POST",
        "/auth/complete-registration",
        payload={
            "email": email.strip().lower(),
            "username": username.strip(),
            "password": password,
            "confirm_password": confirm_password,
        },
    )


def login(identifier, password):
    return api_request(
        "POST",
        "/auth/login",
        payload={
            "identifier": identifier.strip(),
            "password": password,
        },
    )


def get_current_user(token):
    return api_request(
        "GET",
        "/auth/me",
        token=token,
    )


def get_batting_leaderboard(token):
    return api_request(
        "GET",
        "/analytics/batting-leaderboard",
        token=token,
    )


def get_bowling_leaderboard(token):
    return api_request(
        "GET",
        "/analytics/bowling-leaderboard",
        token=token,
    )


def get_match_summary(token):
    return api_request(
        "GET",
        "/analytics/match-summary",
        token=token,
    )


def get_player_stats(token, player_id):
    return api_request(
        "GET",
        f"/analytics/player-stats/{int(player_id)}",
        token=token,
    )

def logout(token):
    return api_request(
        "POST",
        "/auth/logout",
        token=token,
    )


def get_live_matches(token):
    return api_request(
        "GET",
        "/cricbuzz/live-matches",
        token=token,
    )


def get_match_scorecard(match_id: int, token: str):
    return api_request(
        "GET",
        f"/cricbuzz/match-scorecard/{match_id}",
        token=token,
    )


def search_players(token, name):
    return api_request(
        "GET",
        "/cricbuzz/players/search",
        token=token,
        params={"name": name.strip()},
    )


def get_cricbuzz_player_info(token, player_id):
    return api_request(
        "GET",
        f"/cricbuzz/players/{int(player_id)}/info",
        token=token,
    )


def get_cricbuzz_player_career(token, player_id):
    return api_request(
        "GET",
        f"/cricbuzz/players/{int(player_id)}/career",
        token=token,
    )


def get_cricbuzz_player_batting(token, player_id):
    return api_request(
        "GET",
        f"/cricbuzz/players/{int(player_id)}/batting",
        token=token,
    )


def get_cricbuzz_player_bowling(token, player_id):
    return api_request(
        "GET",
        f"/cricbuzz/players/{int(player_id)}/bowling",
        token=token,
    )




def get_match_overview(token):
    return api_request(
        "GET",
        "/analytics/match-overview",
        token=token,
    )


def get_team_match_stats(token):
    return api_request(
        "GET",
        "/analytics/team-match-stats",
        token=token,
    )


def get_match_status_summary(token):
    return api_request(
        "GET",
        "/analytics/match-status-summary",
        token=token,
    )
