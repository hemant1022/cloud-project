"""Inventory Management API entrypoint."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import settings
from .database import Base, SessionLocal, engine, get_db
from .logging_config import configure_logger, get_logger
from .routers import alerts, auth, catalog, catalog_requests, imports, products, stats
from .services.bootstrap import ensure_admin

configure_logger(stack=settings.log_stack, level=settings.log_level_int)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting inventory API | env=%s", settings.database_url.split("@")[-1])
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema ensured")
    except Exception:
        logger.exception("Database schema initialization failed")
        raise

    db = SessionLocal()
    try:
        ensure_admin(db)
    except Exception:
        logger.exception("Admin bootstrap failed; aborting startup")
        raise
    finally:
        db.close()

    logger.info("Startup complete")
    yield
    logger.info("Shutting down inventory API")


app = FastAPI(
    title="Inventory Management API",
    version="1.0.0",
    description="Products, stock, suppliers, categories, CSV import, and low-stock alerts.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    started = time.perf_counter()
    logger.info("Request | %s %s", request.method, request.url.path)
    try:
        response = await call_next(request)
    except Exception:
        elapsed = (time.perf_counter() - started) * 1000
        logger.exception(
            "Request failed | %s %s | %.1f ms",
            request.method,
            request.url.path,
            elapsed,
        )
        raise
    elapsed = (time.perf_counter() - started) * 1000
    logger.info(
        "Response | %s %s -> %s | %.1f ms",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception | %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


@app.get("/", tags=["health"])
def root() -> dict[str, str]:
    return {"service": "inventory-api", "docs": "/docs", "health": "/api/health"}


@app.get("/api/health", tags=["health"])
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
        logger.debug("Health check ok")
        return {"status": "ok", "database": "up"}
    except Exception:
        logger.exception("Health check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from None


app.include_router(auth.router)
app.include_router(products.router)
app.include_router(catalog.router)
app.include_router(alerts.router)
app.include_router(stats.router)
app.include_router(imports.router)
app.include_router(catalog_requests.router)
