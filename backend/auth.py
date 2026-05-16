"""
JWT auth + password hashing.

Owner: Role 1 (Tech Lead).

Other modules use `get_current_user` as a FastAPI dependency:

    from fastapi import Depends
    from backend.auth import get_current_user
    from backend.db import User

    @router.get("/me")
    def me(user: User = Depends(get_current_user)):
        return {"id": user.id, "email": user.email}
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from backend.db import User, get_db

JWT_SECRET = os.getenv("JWT_SECRET", ";~6KNPbpv$3[kq$]vIN}L8")
JWT_ALG = "HS256"
JWT_TTL_HOURS = 24 * 7   # one week is fine for a hackathon

# Admin allowlist: comma-separated emails in ADMIN_EMAILS env var.
# Whoever logs in with one of these is treated as admin (can approve places,
# delete, etc). No DB migration needed — change .env and restart.
ADMIN_EMAILS = {
    e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()
}

_http_bearer = HTTPBearer()

router = APIRouter(tags=["auth"])


# ----- Schemas --------------------------------------------------------------

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    token: str
    user_id: int


# ----- Helpers --------------------------------------------------------------

def hash_password(plain: str) -> str:
    # bcrypt has a hard 72-byte input limit; truncate defensively
    return bcrypt.hashpw(plain.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except ValueError:
        return False


def make_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc)+ timedelta(hours=JWT_TTL_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_http_bearer),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    creds_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise creds_error

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise creds_error
    return user


def is_admin(user: User) -> bool:
    """True if the user's email is in ADMIN_EMAILS."""
    return (user.email or "").lower() in ADMIN_EMAILS


def get_admin_user(user: User = Depends(get_current_user)) -> User:
    """FastAPI dependency that 403s if the caller isn't an admin."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Admin only")
    return user


# ----- Routes ---------------------------------------------------------------

@router.post("/signup", response_model=TokenResponse)
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=body.display_name or body.email.split("@")[0],
        invite_code=secrets.token_hex(3).upper(),  # 6-char invite code
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


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "invite_code": user.invite_code,
        "is_admin": is_admin(user),
    }
