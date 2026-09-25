"""Signup / login / me."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth import (
    get_current_user,
    hash_password,
    is_admin,
    make_token,
    verify_password,
)
from backend.database import get_db
from backend.models import User
from backend.schemas import (
    LoginRequest,
    SignupRequest,
    TokenResponse,
    UserOut,
)

router = APIRouter(tags=["auth"])


def _fresh_invite_code(db: Session) -> str:
    for _ in range(10):
        code = secrets.token_hex(3).upper()
        if not db.query(User).filter(User.invite_code == code).first():
            return code
    return secrets.token_hex(4).upper()


@router.post("/signup", response_model=TokenResponse)
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=body.display_name or body.email.split("@")[0],
        invite_code=_fresh_invite_code(db),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(token=make_token(user.id), user_id=user.id)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return TokenResponse(token=make_token(user.id), user_id=user.id)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        invite_code=user.invite_code,
        is_admin=is_admin(user),
    )
