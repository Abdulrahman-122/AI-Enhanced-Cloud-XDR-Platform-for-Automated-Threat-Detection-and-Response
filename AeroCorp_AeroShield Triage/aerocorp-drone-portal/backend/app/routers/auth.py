from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..logging_setup import log_event
from ..models import User
from ..security import DUMMY_HASH, bearer_claims, client_ip, create_token, limiter, verify_password
from ..util import flag_suspicious

router = APIRouter()

LOCKOUT_FAILURES = 5
LOCKOUT_WINDOW = 900  # seconds


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/api/auth/login")
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request)
    username = payload.username
    flag_suspicious("/api/auth/login", ip, username=username)
    fail_key = f"fail:{username.lower()[:64]}"

    if not settings.vuln_mode:
        if not limiter.allow(f"login-ip:{ip}", 10, 300):
            log_event("rate_limited", client_ip=ip, scope="login")
            raise HTTPException(status_code=429, detail="Too many sign-in attempts. Try again in a few minutes.",
                                headers={"Retry-After": "300"})
        if limiter.count(fail_key, LOCKOUT_WINDOW) >= LOCKOUT_FAILURES:
            log_event("account_locked", client_ip=ip, username=username[:64])
            raise HTTPException(status_code=429, detail="Too many sign-in attempts. Try again in a few minutes.",
                                headers={"Retry-After": "900"})

    user = db.scalar(select(User).where(User.username == username))

    if user is None:
        if not settings.vuln_mode:
            verify_password(payload.password, DUMMY_HASH)
            limiter.record(fail_key)
        log_event("auth_failed", client_ip=ip, username=username[:64], reason="unknown_user")
        raise HTTPException(status_code=401, detail="Unknown user" if settings.vuln_mode else "Invalid username or password.")

    if not verify_password(payload.password, user.password_hash):
        if not settings.vuln_mode:
            limiter.record(fail_key)
        log_event("auth_failed", client_ip=ip, username=username[:64], reason="wrong_password")
        raise HTTPException(status_code=401, detail="Incorrect password" if settings.vuln_mode else "Invalid username or password.")

    limiter.clear(fail_key)
    log_event("auth_success", client_ip=ip, username=user.username, role=user.role)
    return {
        "token": create_token(user.username, user.role),
        "username": user.username,
        "role": user.role,
        "expires_in": settings.token_ttl_seconds,
    }


@router.get("/api/auth/me")
def me(request: Request):
    claims = bearer_claims(request)
    if claims is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return {"username": claims["sub"], "role": claims["role"]}
