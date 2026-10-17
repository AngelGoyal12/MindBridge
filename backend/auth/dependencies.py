
import hashlib
import secrets
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from auth.sessions import SESSION_COOKIE_NAME
from auth.roles import ROLE_VALUES
from database import SessionLocal
from models import User, UserSession


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    request: Request,
    db: DbSession,
) -> User:
    token = request.cookies.get(SESSION_COOKIE_NAME)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    session_record = (
        db.query(UserSession)
        .filter(
            UserSession.token_hash == token_hash,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )

    if session_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session.",
        )

    user = (
        db.query(User)
        .filter(User.id == session_record.user_id)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    if user.role not in ROLE_VALUES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account role is not authorized.",
        )

    if user.role == "department_staff" and not (user.department or "").strip():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Department assignment is required for this account.",
        )

    return user


def require_roles(*allowed_roles: str) -> Callable:
    permitted = frozenset(allowed_roles)

    if not permitted or not permitted.issubset(ROLE_VALUES):
        raise ValueError("At least one valid role must be required.")

    def role_dependency(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in permitted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this resource.",
            )

        if (
            current_user.role == "department_staff"
            and not (current_user.department or "").strip()
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Department assignment is required for this account.",
            )

        return current_user

    return role_dependency


def require_csrf_token(
    request: Request,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    if not csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token required",
        )

    session_token = request.cookies.get(SESSION_COOKIE_NAME)

    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    session_hash = hashlib.sha256(
        session_token.encode("utf-8")
    ).hexdigest()

    session_record = (
        db.query(UserSession)
        .filter(
            UserSession.token_hash == session_hash,
            UserSession.user_id == current_user.id,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )

    if (
        not session_record
        or not session_record.csrf_token_hash
        or not secrets.compare_digest(
            hashlib.sha256(
                csrf_token.encode("utf-8")
            ).hexdigest(),
            session_record.csrf_token_hash,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token",
        )
