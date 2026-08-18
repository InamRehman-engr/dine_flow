"""JWT access tokens + refresh cookie helpers for staff auth."""
from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from typing import Any

import jwt
from flask import current_app, request

from models import utcnow


def _jwt_secret() -> str:
    return current_app.config["JWT_SECRET_KEY"]


def create_access_token(staff_user, tenant) -> str:
    now = utcnow()
    hours = float(current_app.config.get("JWT_ACCESS_HOURS", 1))
    payload = {
        "typ": "access",
        "sub": str(staff_user.id),
        "tid": str(tenant.id),
        "role": staff_user.role,
        "email": staff_user.email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=hours)).timestamp()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
        if payload.get("typ") != "access":
            return None
        return payload
    except (jwt.PyJWTError, ValueError, TypeError):
        return None


def create_guest_socket_ticket(table) -> str:
    now = utcnow()
    hours = float(current_app.config.get("GUEST_SOCKET_HOURS", 12))
    payload = {
        "typ": "guest_socket",
        "tid": str(table.tenant_id),
        "table_id": str(table.id),
        "table_number": table.number,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=hours)).timestamp()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def decode_guest_socket_ticket(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
        if payload.get("typ") != "guest_socket":
            return None
        return payload
    except (jwt.PyJWTError, ValueError, TypeError):
        return None


def new_refresh_raw() -> str:
    return secrets.token_urlsafe(48)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def bearer_token_from_request() -> str | None:
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return None
