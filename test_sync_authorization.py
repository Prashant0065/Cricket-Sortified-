from unittest.mock import patch
from fastapi import HTTPException
from backend.api.routes.sync import sync_live_match_metadata_route

with patch("backend.api.routes.sync.sync_live_match_metadata") as mock_sync:
    mock_sync.return_value = {
        "mode": "dry_run",
        "database_changed": False
    }

    result = sync_live_match_metadata_route(
        dry_run=True,
        current_user={"user_id": 7}
    )
    print("Regular user dry-run:", result["database_changed"] is False)

    try:
        sync_live_match_metadata_route(
            dry_run=False,
            current_user={"user_id": 7}
        )
    except HTTPException as error:
        print("Regular user commit blocked:", error.status_code == 403)

    result = sync_live_match_metadata_route(
        dry_run=False,
        current_user={"user_id": 4}
    )
    print("Admin authorization passed:", result["database_changed"] is False)
    print("Synchronization service called:", mock_sync.call_count)
