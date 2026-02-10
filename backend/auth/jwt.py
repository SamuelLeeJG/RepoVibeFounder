"""JWT token creation and validation — pure stdlib HMAC-SHA256 implementation."""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import json
import uuid
from typing import Any

from backend.config import settings

SECRET = settings.jwt_secret_key


class JWTError(Exception):
    """JWT validation error."""
    pass


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def _sign(header_payload: str) -> str:
    sig = hmac.new(SECRET.encode(), header_payload.encode(), hashlib.sha256).digest()
    return _b64url_encode(sig)


def _encode_jwt(payload: dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    # Convert datetime to timestamp for JSON serialization
    p = {}
    for k, v in payload.items():
        if isinstance(v, dt.datetime):
            p[k] = int(v.timestamp())
        else:
            p[k] = v
    b = _b64url_encode(json.dumps(p, separators=(",", ":")).encode())
    header_payload = f"{h}.{b}"
    sig = _sign(header_payload)
    return f"{header_payload}.{sig}"


def _decode_jwt(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise JWTError("Invalid token format")
    header_payload = f"{parts[0]}.{parts[1]}"
    expected_sig = _sign(header_payload)
    if not hmac.compare_digest(expected_sig, parts[2]):
        raise JWTError("Invalid signature")
    try:
        payload = json.loads(_b64url_decode(parts[1]))
    except (json.JSONDecodeError, Exception) as e:
        raise JWTError(f"Invalid payload: {e}")
    # Check expiration
    exp = payload.get("exp")
    if exp is not None:
        now = dt.datetime.now(dt.timezone.utc).timestamp()
        if now > exp:
            raise JWTError("Token expired")
    return payload


def create_access_token(subject: str | uuid.UUID, extra: dict[str, Any] | None = None) -> str:
    """Create a short-lived access token."""
    expire = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {"sub": str(subject), "exp": expire, "type": "access"}
    if extra:
        payload.update(extra)
    return _encode_jwt(payload)


def create_refresh_token(subject: str | uuid.UUID) -> str:
    """Create a long-lived refresh token."""
    expire = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {"sub": str(subject), "exp": expire, "type": "refresh"}
    return _encode_jwt(payload)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token. Raises JWTError on failure."""
    return _decode_jwt(token)


def verify_access_token(token: str) -> str:
    """Verify an access token and return the subject (user ID). Raises JWTError if invalid."""
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise JWTError("Not an access token")
    sub = payload.get("sub")
    if sub is None:
        raise JWTError("Missing subject")
    return sub


def verify_refresh_token(token: str) -> str:
    """Verify a refresh token and return the subject (user ID). Raises JWTError if invalid."""
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise JWTError("Not a refresh token")
    sub = payload.get("sub")
    if sub is None:
        raise JWTError("Missing subject")
    return sub
