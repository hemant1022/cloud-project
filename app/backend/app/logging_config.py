"""Central logging configuration for the project.

Every event is written to two rotating files plus the console:

1. Combined log (all runs, all stacks): ``logs/combined/combined.log``
2. Per-run stack log:                   ``logs/<stack>/<stack>-<timestamp>.log``

Log line format::

    [ 2026-07-27 16:17:41,978 ] httpx - INFO - HTTP Request: GET ... 200 OK

Usage::

    from app.logging_config import configure_logger, get_logger

    configure_logger(stack="backend")
    logger = get_logger(__name__)
    logger.info("backend started")
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FORMAT = "[ %(asctime)s ] %(name)s - %(levelname)s - %(message)s"
MAX_LOG_SIZE = 5 * 1024 * 1024
BACKUP_COUNT = 3
DEFAULT_STACK = "backend"
ALLOWED_STACKS = ("backend", "frontend", "docker", "terraform", "ci", "argocd", "monitoring")

_SESSION_TS = datetime.now().strftime("%m_%d_%Y_%H_%M_%S")
_HANDLER_MARKER = "_cloud_project_handler"
_CONFIGURED = False


def project_root() -> Path:
    """Return the repository root (override with the PROJECT_ROOT env var).

    Works both in the repository layout (repo/app/backend/app/logging_config.py)
    and inside the container (app/app/logging_config.py).
    """
    override = os.getenv("PROJECT_ROOT")
    if override:
        return Path(override).resolve()
    parents = Path(__file__).resolve().parents
    if len(parents) > 3:
        return parents[3]
    if len(parents) > 1:
        return parents[1]
    return parents[0]


def _build_file_handler(path: Path, level: int) -> RotatingFileHandler:
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        path,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.setLevel(level)
    setattr(handler, _HANDLER_MARKER, True)
    return handler


def _build_console_handler(level: int) -> logging.StreamHandler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.setLevel(level)
    setattr(handler, _HANDLER_MARKER, True)
    return handler


def configure_logger(stack: str | None = None, level: int = logging.INFO, force: bool = False) -> logging.Logger:
    """Configure the root logger with combined, per-stack, and console handlers."""
    global _CONFIGURED

    stack = (stack or os.getenv("LOG_STACK") or DEFAULT_STACK).strip().lower()
    if stack not in ALLOWED_STACKS:
        raise ValueError(f"Unknown stack '{stack}'. Expected one of: {', '.join(ALLOWED_STACKS)}")

    logger = logging.getLogger()
    if _CONFIGURED and not force:
        return logger

    for handler in list(logger.handlers):
        if getattr(handler, _HANDLER_MARKER, False):
            logger.removeHandler(handler)
            handler.close()

    log_root = Path(os.getenv("LOG_DIR") or (project_root() / "logs"))
    combined_path = log_root / "combined" / "combined.log"
    stack_path = log_root / stack / f"{stack}-{_SESSION_TS}.log"

    logger.setLevel(logging.DEBUG)
    logger.addHandler(_build_file_handler(combined_path, level))
    logger.addHandler(_build_file_handler(stack_path, level))
    logger.addHandler(_build_console_handler(level))
    logger.propagate = False

    _CONFIGURED = True
    install_exception_hook(logger)

    logger.debug("Logging ready | stack=%s | combined=%s | run=%s", stack, combined_path, stack_path)
    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a named logger that inherits the configured root handlers."""
    return logging.getLogger(name)


def install_exception_hook(logger: logging.Logger) -> None:
    """Log uncaught exceptions to the combined and per-stack files."""

    def _handle(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = _handle


if __name__ == "__main__":
    configure_logger(stack=os.getenv("LOG_STACK", DEFAULT_STACK), force=True)
    demo = get_logger("logging_config")
    demo.info("Logging self-test started")
    demo.debug("Debug message is written to file but hidden on the console")
    demo.warning("This warning appears in both logs")
    demo.info("Logging self-test finished")
