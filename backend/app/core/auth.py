from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

import sqlalchemy as sa
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

_bearer = HTTPBearer()


def create_access_token(user_id: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_ttl_minutes)
    return jwt.encode(
        {"sub": user_id, "exp": expires},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> str:
    """Decode and validate a JWT; return the user_id (sub claim)."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")
        return user_id
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Validate JWT and load the full user record from the DB on every request.

    Role is never trusted from the token — always read from the database so
    that role revocation takes effect immediately.
    """
    user_id = decode_token(credentials.credentials)
    row = db.execute(
        sa.text("SELECT id, email, role FROM users WHERE id = :id"),
        {"id": user_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return {"id": str(row[0]), "email": row[1], "role": row[2]}


def require_admin(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Raise 403 if the authenticated user does not have the admin role."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return current_user
