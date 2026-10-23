
import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from pwdlib import PasswordHash

from backend.api.dependencies import get_current_user
from backend.database.connection import get_connection
from backend.utils.email_service import send_email


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

router = APIRouter(prefix="/auth", tags=["Authentication"])
bearer_scheme = HTTPBearer(auto_error=False)
password_hash = PasswordHash.recommended()


def get_secret_key():
    secret = os.getenv("JWT_SECRET_KEY")

    if not secret or secret == "YOUR_GENERATED_RANDOM_SECRET":
        raise HTTPException(
            status_code=500,
            detail="JWT authentication is not configured.",
        )

    return secret


def get_otp_hash(email: str, otp: str) -> str:
    message = f"{email}:{otp}".encode("utf-8")
    return hmac.new(
        get_secret_key().encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()



def create_access_token(user_id: int, username: str) -> str:
    secret = get_secret_key()
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    expiry_minutes = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=expiry_minutes)

    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": expires_at,
    }

    access_token = jwt.encode(
        payload,
        secret,
        algorithm=algorithm,
    )

    token_hash = hashlib.sha256(
        access_token.encode("utf-8")
    ).hexdigest()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_sessions
                    (user_id, token_hash, expires_at)
                VALUES (%s, %s, %s);
                """,
                (user_id, token_hash, expires_at),
            )

    return access_token



def validate_password(password: str):
    if len(password) < 8 or len(password) > 128:
        raise HTTPException(
            status_code=422,
            detail="Password must contain between 8 and 128 characters.",
        )

    if not re.search(r"[a-z]", password):
        raise HTTPException(
            status_code=422,
            detail="Password must contain a lowercase letter.",
        )

    if not re.search(r"[A-Z]", password):
        raise HTTPException(
            status_code=422,
            detail="Password must contain an uppercase letter.",
        )

    if not re.search(r"\d", password):
        raise HTTPException(
            status_code=422,
            detail="Password must contain a digit.",
        )

    if not re.search(r"[^A-Za-z0-9]", password):
        raise HTTPException(
            status_code=422,
            detail="Password must contain a special character.",
        )


class SendOTPRequest(BaseModel):
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(pattern=r"^[0-9]{6}$")


class CompleteRegistrationRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=128)


@router.post("/send-otp")
def send_registration_otp(data: SendOTPRequest):
    email = str(data.email).strip().lower()
    otp = f"{secrets.randbelow(1_000_000):06d}"
    otp_hash = get_otp_hash(email, otp)

    expiry_minutes = int(os.getenv("OTP_EXPIRY_MINUTES", "10"))
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=expiry_minutes
    )

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 1
                    FROM users
                    WHERE LOWER(email) = %s
                    LIMIT 1;
                    """,
                    (email,),
                )

                if cur.fetchone():
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "An account with this email already exists. "
                            "Please sign in instead."
                        ),
                    )

                cur.execute(
                    """
                    UPDATE email_verification_challenges
                    SET consumed_at = CURRENT_TIMESTAMP
                    WHERE LOWER(email) = %s
                      AND consumed_at IS NULL;
                    """,
                    (email,),
                )

                cur.execute(
                    """
                    INSERT INTO email_verification_challenges
                        (email, otp_hash, expires_at)
                    VALUES (%s, %s, %s);
                    """,
                    (email, otp_hash, expires_at),
                )

                send_email(
                    recipient=email,
                    subject="Cricbuzz LiveStats - Verify Your Email",
                    body=(
                        "Hello,\n\n"
                        f"Your email verification code is: {otp}\n\n"
                        f"This code expires in {expiry_minutes} minutes.\n"
                        "Do not share this code with anyone.\n\n"
                        "Cricbuzz LiveStats Team"
                    ),
                )

        return {
            "message": (
                "Verification code sent. Please check your email."
            )
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to send verification code.",
        ) from error


@router.post("/resend-otp")
def resend_registration_otp(data: SendOTPRequest):
    email = str(data.email).strip().lower()
    otp = f"{secrets.randbelow(1_000_000):06d}"
    otp_hash = get_otp_hash(email, otp)

    expiry_minutes = int(os.getenv("OTP_EXPIRY_MINUTES", "10"))
    cooldown_seconds = int(os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "60"))
    max_requests = int(os.getenv("OTP_MAX_RESENDS_PER_HOUR", "5"))

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=expiry_minutes
    )

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 1
                    FROM users
                    WHERE LOWER(email) = %s
                    LIMIT 1;
                    """,
                    (email,),
                )

                if cur.fetchone():
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "An account with this email already exists. "
                            "Please sign in instead."
                        ),
                    )

                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM email_verification_challenges
                    WHERE LOWER(email) = %s
                      AND created_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour';
                    """,
                    (email,),
                )
                requests_last_hour = cur.fetchone()[0]

                if requests_last_hour >= max_requests:
                    raise HTTPException(
                        status_code=429,
                        detail=(
                            "Too many verification-code requests. "
                            "Please try again later."
                        ),
                    )

                cur.execute(
                    """
                    SELECT created_at
                    FROM email_verification_challenges
                    WHERE LOWER(email) = %s
                    ORDER BY created_at DESC, challenge_id DESC
                    LIMIT 1;
                    """,
                    (email,),
                )
                latest = cur.fetchone()

                if latest:
                    elapsed = (
                        datetime.now(timezone.utc) - latest[0]
                    ).total_seconds()

                    if elapsed < cooldown_seconds:
                        wait_seconds = max(
                            1,
                            int(cooldown_seconds - elapsed),
                        )
                        raise HTTPException(
                            status_code=429,
                            detail=(
                                "Please wait "
                                f"{wait_seconds} seconds before requesting "
                                "another verification code."
                            ),
                        )

                cur.execute(
                    """
                    UPDATE email_verification_challenges
                    SET consumed_at = CURRENT_TIMESTAMP
                    WHERE LOWER(email) = %s
                      AND consumed_at IS NULL;
                    """,
                    (email,),
                )

                cur.execute(
                    """
                    INSERT INTO email_verification_challenges
                        (email, otp_hash, expires_at)
                    VALUES (%s, %s, %s);
                    """,
                    (email, otp_hash, expires_at),
                )

                send_email(
                    recipient=email,
                    subject="Cricbuzz LiveStats - New Verification Code",
                    body=(
                        "Hello,\n\n"
                        f"Your new verification code is: {otp}\n\n"
                        f"This code expires in {expiry_minutes} minutes.\n"
                        "Only the latest code can be used.\n"
                        "Do not share this code with anyone.\n\n"
                        "Cricbuzz LiveStats Team"
                    ),
                )

        return {
            "message": (
                "A new verification code has been sent. "
                "Please check your email."
            )
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to resend verification code.",
        ) from error


@router.post("/verify-otp")
def verify_email_otp(data: VerifyOTPRequest):
    email = str(data.email).strip().lower()
    max_attempts = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))

    outcome = None

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT challenge_id, otp_hash, expires_at,
                           attempt_count, verified_at
                    FROM email_verification_challenges
                    WHERE LOWER(email) = %s
                      AND consumed_at IS NULL
                    ORDER BY created_at DESC, challenge_id DESC
                    LIMIT 1
                    FOR UPDATE;
                    """,
                    (email,),
                )

                challenge = cur.fetchone()

                if not challenge:
                    outcome = (
                        400,
                        "No active verification code. "
                        "Please request a new code.",
                    )
                else:
                    (
                        challenge_id,
                        stored_hash,
                        expires_at,
                        attempts,
                        verified_at,
                    ) = challenge

                    if verified_at is not None:
                        outcome = (
                            400,
                            "Email already verified. Complete registration.",
                        )

                    elif attempts >= max_attempts:
                        outcome = (
                            429,
                            "Maximum verification attempts reached. "
                            "Request a new code.",
                        )

                    elif expires_at <= datetime.now(timezone.utc):
                        cur.execute(
                            """
                            UPDATE email_verification_challenges
                            SET consumed_at = CURRENT_TIMESTAMP
                            WHERE challenge_id = %s;
                            """,
                            (challenge_id,),
                        )
                        outcome = (
                            400,
                            "Verification code has expired. "
                            "Request a new code.",
                        )

                    else:
                        submitted_hash = get_otp_hash(email, data.otp)

                        if not hmac.compare_digest(
                            stored_hash,
                            submitted_hash,
                        ):
                            cur.execute(
                                """
                                UPDATE email_verification_challenges
                                SET attempt_count = attempt_count + 1,
                                    consumed_at = CASE
                                        WHEN attempt_count + 1 >= %s
                                        THEN CURRENT_TIMESTAMP
                                        ELSE consumed_at
                                    END
                                WHERE challenge_id = %s;
                                """,
                                (max_attempts, challenge_id),
                            )

                            outcome = (
                                400,
                                "Invalid verification code.",
                            )
                        else:
                            cur.execute(
                                """
                                UPDATE email_verification_challenges
                                SET verified_at = CURRENT_TIMESTAMP,
                                    consumed_at = CURRENT_TIMESTAMP
                                WHERE challenge_id = %s;
                                """,
                                (challenge_id,),
                            )

        if outcome:
            code, message = outcome
            raise HTTPException(
                status_code=code,
                detail=message,
            )

        return {
            "message": "Email verified successfully."
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to verify email.",
        ) from error


@router.post("/complete-registration")
def complete_registration(data: CompleteRegistrationRequest):
    email = str(data.email).strip().lower()
    username = data.username.strip()

    if len(username) < 3:
        raise HTTPException(
            status_code=422,
            detail="Username must contain at least 3 characters.",
        )

    if data.password != data.confirm_password:
        raise HTTPException(
            status_code=422,
            detail="Passwords do not match.",
        )

    validate_password(data.password)

    hashed_password = password_hash.hash(data.password)
    result = None

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT challenge_id
                    FROM email_verification_challenges
                    WHERE LOWER(email) = %s
                      AND verified_at IS NOT NULL
                      AND verified_at >=
                          CURRENT_TIMESTAMP - INTERVAL '30 minutes'
                    ORDER BY verified_at DESC, challenge_id DESC
                    LIMIT 1
                    FOR UPDATE;
                    """,
                    (email,),
                )

                challenge = cur.fetchone()

                if not challenge:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Email verification is missing or has expired. "
                            "Please verify your email again."
                        ),
                    )

                cur.execute(
                    """
                    INSERT INTO users
                        (email, username, password_hash, is_email_verified)
                    VALUES (%s, %s, %s, TRUE)
                    RETURNING user_id, email, username,
                              is_email_verified, is_active;
                    """,
                    (email, username, hashed_password),
                )

                user = cur.fetchone()

                cur.execute(
                    """
                    UPDATE email_verification_challenges
                    SET verified_at = NULL
                    WHERE challenge_id = %s;
                    """,
                    (challenge[0],),
                )

                result = {
                    "user_id": user[0],
                    "email": user[1],
                    "username": user[2],
                    "is_email_verified": user[3],
                    "is_active": user[4],
                }

        token = create_access_token(
            result["user_id"],
            result["username"],
        )

        return {
            "message": "Registration successful.",
            "access_token": token,
            "token_type": "bearer",
            "user": result,
        }

    except HTTPException:
        raise
    except Exception as error:
        if getattr(error, "sqlstate", None) == "23505":
            raise HTTPException(
                status_code=409,
                detail="Email or username is already registered.",
            ) from error

        raise HTTPException(
            status_code=500,
            detail="Unable to complete registration.",
        ) from error


@router.post("/login")
def login_user(data: LoginRequest):
    identifier = data.identifier.strip()

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT user_id, email, username, password_hash,
                           is_email_verified, is_active
                    FROM users
                    WHERE LOWER(email) = LOWER(%s)
                       OR LOWER(username) = LOWER(%s)
                    LIMIT 1;
                    """,
                    (identifier, identifier),
                )
                user = cur.fetchone()

        if not user or not password_hash.verify(data.password, user[3]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email/username or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id, email, username, _, verified, active = user

        if not active:
            raise HTTPException(
                status_code=403,
                detail="This account is inactive.",
            )

        if not verified:
            raise HTTPException(
                status_code=403,
                detail="Please verify your email before signing in.",
            )

        token = create_access_token(user_id, username)

        return {
            "message": "Login successful.",
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "user_id": user_id,
                "email": email,
                "username": username,
                "is_email_verified": verified,
                "is_active": active,
            },
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to sign in.",
        ) from error


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


@router.post("/logout")
def logout_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    current_user: dict = Depends(get_current_user),
):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication is required.",
        )

    token_hash = hashlib.sha256(
        credentials.credentials.encode("utf-8")
    ).hexdigest()

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE user_sessions
                    SET revoked_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                      AND token_hash = %s
                      AND revoked_at IS NULL
                    RETURNING session_id;
                    """,
                    (current_user["user_id"], token_hash),
                )

                revoked_session = cur.fetchone()

        if not revoked_session:
            raise HTTPException(
                status_code=401,
                detail="Session is already revoked or does not exist.",
            )

        return {"message": "Logged out successfully."}

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail="Unable to revoke the session.",
        ) from error
