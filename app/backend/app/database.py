"""Database engine, session factory, and dependency."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .config import settings
from .logging_config import get_logger

logger = get_logger(__name__)

_is_sqlite = settings.database_url.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}

try:
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
        connect_args=_connect_args,
    )
    logger.info("Database engine created | dialect=%s", engine.dialect.name)
except Exception:
    logger.exception("Failed to create database engine")
    raise

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        logger.exception("Database session error; rolling back")
        db.rollback()
        raise
    finally:
        db.close()
