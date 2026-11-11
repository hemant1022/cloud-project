"""Startup bootstrap: ensure the first admin account exists."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..logging_config import get_logger
from ..models import User
from ..security import hash_password

logger = get_logger(__name__)


def ensure_admin(db: Session) -> User:
    email = settings.admin_email.strip().lower()
    try:
        existing = db.scalar(select(User).where(func.lower(User.email) == email))
        if existing is not None:
            logger.info("Admin account already present | email=%s", existing.email)
            return existing

        admin = User(
            email=email,
            password_hash=hash_password(settings.admin_password),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        logger.info("Admin account created | email=%s", admin.email)
        return admin
    except Exception:
        db.rollback()
        logger.exception("Failed to ensure admin account | email=%s", email)
        raise
