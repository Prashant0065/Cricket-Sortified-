
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import get_current_user
from backend.services.cricbuzz_client import (
    CricbuzzAPIError,
    get_live_matches,
    get_match_scorecard,
    search_players,
    get_player_info,
    get_player_career,
    get_player_batting,
    get_player_bowling,
)


router = APIRouter(
    prefix="/cricbuzz",
    tags=["Cricbuzz"],
)


def handle_cricbuzz_error(error: CricbuzzAPIError):
    raise HTTPException(
        status_code=502,
        detail=str(error),
    ) from error


def validate_response_object(data, label: str) -> dict:
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=502,
            detail=f"Unexpected {label} response from Cricbuzz.",
        )
    return data


@router.get("/live-matches")
def live_matches(
    current_user: dict = Depends(get_current_user),
):
    try:
        return validate_response_object(
            get_live_matches(),
            "live-matches",
        )
    except CricbuzzAPIError as error:
        handle_cricbuzz_error(error)


@router.get("/match-scorecard/{match_id}")
def match_scorecard(
    match_id: int,
    current_user: dict = Depends(get_current_user),
):
    if match_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="Match ID must be a positive integer.",
        )

    try:
        return validate_response_object(
            get_match_scorecard(match_id),
            "scorecard",
        )
    except CricbuzzAPIError as error:
        handle_cricbuzz_error(error)


@router.get("/players/search")
def player_search(
    name: str = Query(..., min_length=1, max_length=100),
    current_user: dict = Depends(get_current_user),
):
    if not name.strip():
        raise HTTPException(
            status_code=422,
            detail="Enter a player name to search.",
        )

    try:
        return validate_response_object(
            search_players(name),
            "player-search",
        )
    except CricbuzzAPIError as error:
        handle_cricbuzz_error(error)


@router.get("/players/{player_id}/info")
def player_info(
    player_id: int,
    current_user: dict = Depends(get_current_user),
):
    if player_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="Player ID must be a positive integer.",
        )

    try:
        return validate_response_object(
            get_player_info(player_id),
            "player-info",
        )
    except CricbuzzAPIError as error:
        handle_cricbuzz_error(error)


@router.get("/players/{player_id}/career")
def player_career(
    player_id: int,
    current_user: dict = Depends(get_current_user),
):
    if player_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="Player ID must be a positive integer.",
        )

    try:
        return validate_response_object(
            get_player_career(player_id),
            "player-career",
        )
    except CricbuzzAPIError as error:
        handle_cricbuzz_error(error)


@router.get("/players/{player_id}/batting")
def player_batting(
    player_id: int,
    series_id: int | None = Query(default=None, gt=0),
    current_user: dict = Depends(get_current_user),
):
    if player_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="Player ID must be a positive integer.",
        )

    try:
        return validate_response_object(
            get_player_batting(
                player_id,
                series_id=series_id,
            ),
            "batting-statistics",
        )
    except CricbuzzAPIError as error:
        handle_cricbuzz_error(error)


@router.get("/players/{player_id}/bowling")
def player_bowling(
    player_id: int,
    series_id: int | None = Query(default=None, gt=0),
    current_user: dict = Depends(get_current_user),
):
    if player_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="Player ID must be a positive integer.",
        )

    try:
        return validate_response_object(
            get_player_bowling(
                player_id,
                series_id=series_id,
            ),
            "bowling-statistics",
        )
    except CricbuzzAPIError as error:
        handle_cricbuzz_error(error)
