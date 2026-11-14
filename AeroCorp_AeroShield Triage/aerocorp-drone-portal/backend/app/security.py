"""Password hashing, signed tokens, rate limiting and small helpers (standard library only)."""
import base64
import hashlib
import hmac
import json
import os
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from .config import settings

PBKDF2_ITERATIONS = 120_000


# --------------------------------------------------------------------------- passwords
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.b64encode(salt).decode(),
        base64.b64encode(digest).decode(),
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt_b64, digest_b64 = stored.split("$")
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except Exception:  # noqa: BLE001
        return False


# A valid hash of a random value, used so "unknown user" takes as long as "wrong password".
DUMMY_HASH = hash_password(base64.b64encode(os.urandom(12)).decode())


# --------------------------------------------------------------------------- tokens
def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(body: str) -> str:
    return _b64(hmac.new(settings.secret_key.encode(), body.encode(), hashlib.sha256).digest())


def create_token(username: str, role: str, ttl: int | None = None) -> str:
    payload = {"sub": username, "role": role, "exp": int(time.time()) + (ttl or settings.token_ttl_seconds)}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    return f"{body}.{_sign(body)}"


def verify_token(token: str) -> dict | None:
    try:
        body, signature = token.split(".")
        if not hmac.compare_digest(signature, _sign(body)):
            return None
        payload = json.loads(_unb64(body))
        if int(payload["exp"]) < time.time():
            return None
        return payload
    except Exception:  # noqa: BLE001
        return None


def bearer_claims(request: Request) -> dict | None:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return verify_token(header[7:].strip())
    return None


def require_admin(request: Request) -> dict:
    claims = bearer_claims(request)
    if claims is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if claims.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return claims


def require_staff(request: Request) -> dict:
    """Admins and sales staff. Customer tokens are refused."""
    claims = bearer_claims(request)
    if claims is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if claims.get("role") not in ("admin", "sales"):
        raise HTTPException(status_code=403, detail="Staff role required")
    return claims


def customer_id_from(request: Request) -> int | None:
    """The signed-in customer's id, or None for anonymous or staff tokens."""
    claims = bearer_claims(request)
    if claims is None or claims.get("role") != "customer":
        return None
    try:
        return int(claims["sub"])
    except (TypeError, ValueError):
        return None


def require_customer(request: Request) -> int:
    claims = bearer_claims(request)
    if claims is None:
        raise HTTPException(status_code=401, detail="Sign in to your account first.")
    if claims.get("role") != "customer":
        raise HTTPException(status_code=403, detail="This page is for customer accounts.")
    return int(claims["sub"])


# --------------------------------------------------------------------------- client ip
def client_ip(request: Request) -> str:
    """NGINX sets X-Real-IP. Direct connections (local dev) fall back to the socket address."""
    forwarded = request.headers.get("x-real-ip")
    if forwarded:
        return forwarded.strip()[:64]
    return request.client.host if request.client else "unknown"


# --------------------------------------------------------------------------- rate limiting
class RateLimiter:
    """Small in-memory sliding-window limiter. Good enough for one backend container."""

    def __init__(self) -> None:
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, window: float, now: float) -> deque:
        hits = self._hits[key]
        while hits and hits[0] <= now - window:
            hits.popleft()
        return hits

    def allow(self, key: str, limit: int, window: float) -> bool:
        """Record a hit and return False once more than `limit` hits fall inside `window` seconds."""
        now = time.monotonic()
        with self._lock:
            hits = self._prune(key, window, now)
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True

    def count(self, key: str, window: float) -> int:
        with self._lock:
            return len(self._prune(key, window, time.monotonic()))

    def record(self, key: str) -> None:
        with self._lock:
            self._hits[key].append(time.monotonic())

    def clear(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()
