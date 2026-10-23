
import hashlib
import os
from pathlib import Path

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.database.connection import get_connection


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid, expired, or revoked access token. Please sign in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    token = credentials.credentials
    secret = os.getenv("JWT_SECRET_KEY")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")

    if not secret or secret == "YOUR_GENERATED_RANDOM_SECRET":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT authentication is not configured.",
        )

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[algorithm],
            options={"require": ["sub", "exp"]},
        )
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError):
        raise unauthorized

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT u.user_id, u.email, u.username,
                           u.is_email_verified, u.is_active
                    FROM users AS u
                    JOIN user_sessions AS s
                      ON s.user_id = u.user_id
                    WHERE u.user_id = %s
                      AND s.token_hash = %s
                      AND s.revoked_at IS NULL
                      AND s.expires_at > CURRENT_TIMESTAMP
                    LIMIT 1;
                    """,
                    (user_id, token_hash),
                )
                user = cur.fetchone()

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify account session.",
        ) from error

    if user is None or not user[3] or not user[4]:
        raise unauthorized

    return {
        "user_id": user[0],
        "email": user[1],
        "username": user[2],
    }
