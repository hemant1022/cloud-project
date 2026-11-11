"""Shared FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .logging_config import get_logger
from .models import User
from .security import decode_token

logger = get_logger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        logger.warning("Rejected expired token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from None
    except jwt.PyJWTError:
        logger.warning("Rejected invalid token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from None

    try:
        user_id = int(payload.get("sub", ""))
    except (TypeError, ValueError):
        logger.warning("Token subject is not a valid user id | sub=%s", payload.get("sub"))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject") from None

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        logger.warning("Rejected token for inactive/unknown user | user_id=%s", user_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")

    return user


def require_roles(*roles: str) -> Callable[..., User]:
    allowed = set(roles)

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            logger.warning("Forbidden access | user=%s role=%s required=%s", user.email, user.role, sorted(allowed))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(sorted(allowed))}",
            )
        return user

    return checker
