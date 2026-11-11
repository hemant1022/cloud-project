"""Password hashing and JWT helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash

from .config import settings
from .logging_config import get_logger

logger = get_logger(__name__)

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    try:
        return password_hasher.hash(password)
    except Exception:
        logger.exception("Password hashing failed")
        raise


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password, password_hash)
    except Exception:
        logger.exception("Password verification failed")
        return False


def create_access_token(subject: str, role: str, expires_minutes: int | None = None) -> tuple[str, int]:
    minutes = expires_minutes or settings.jwt_expire_minutes
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    try:
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        logger.debug("Access token issued | subject=%s role=%s", subject, role)
        return token, minutes * 60
    except Exception:
        logger.exception("Token creation failed | subject=%s", subject)
        raise


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
