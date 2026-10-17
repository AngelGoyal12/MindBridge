
import hashlib
import secrets
import os
from datetime import datetime, timedelta, timezone

from fastapi import Response
from sqlalchemy.orm import Session

from models import User, UserSession


SESSION_COOKIE_NAME = "mindbridge_session"
SESSION_DURATION_HOURS = 8

def resolve_cookie_secure(app_env: str, secure_setting: str) -> bool:
    environment = app_env.strip().lower()
    setting = secure_setting.strip().lower()
    if setting not in {"", "true", "false"}:
        raise RuntimeError("SESSION_COOKIE_SECURE must be 'true' or 'false'.")
    if environment in {"production", "prod"} and setting != "true":
        raise RuntimeError(
            "SESSION_COOKIE_SECURE=true is required when APP_ENV is production."
        )
    return setting == "true"


COOKIE_SECURE = resolve_cookie_secure(
    os.getenv("APP_ENV", "development"),
    os.getenv("SESSION_COOKIE_SECURE", ""),
)


def create_session(
    db: Session,
    user: User,
    response: Response,
) -> str:
    # Generate secure, unpredictable session and CSRF tokens.
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    csrf_token = secrets.token_urlsafe(32)
    csrf_token_hash = hashlib.sha256(
        csrf_token.encode("utf-8")
    ).hexdigest()

    now = datetime.now(timezone.utc)

    session_record = UserSession(
        user_id=user.id,
        token_hash=token_hash,
        csrf_token_hash=csrf_token_hash,
        created_at=now,
        expires_at=now + timedelta(hours=SESSION_DURATION_HOURS),
    )

    try:
        db.add(session_record)
        db.commit()
    except Exception:
        db.rollback()
        raise

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_DURATION_HOURS * 60 * 60,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )

    return csrf_token


def revoke_session(
    db: Session,
    token: str | None,
) -> None:
    if not token:
        return

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    session_record = (
        db.query(UserSession)
        .filter(
            UserSession.token_hash == token_hash,
            UserSession.revoked_at.is_(None),
        )
        .first()
    )

    if session_record:
        session_record.revoked_at = datetime.now(timezone.utc)
        db.commit()


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
    )
