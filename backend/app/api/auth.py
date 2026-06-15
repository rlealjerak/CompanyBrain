from __future__ import annotations

from typing import Annotated

import bcrypt
import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import create_access_token, get_current_user
from app.core.database import get_db

router = APIRouter(prefix="/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    row = db.execute(
        sa.text("SELECT id, hashed_password FROM users WHERE email = :email"),
        {"email": body.email},
    ).fetchone()

    if not row or not bcrypt.checkpw(body.password.encode(), row[1].encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return {"access_token": create_access_token(str(row[0]))}


@router.get("/me")
def me(current_user: Annotated[dict, Depends(get_current_user)]):
    return current_user
