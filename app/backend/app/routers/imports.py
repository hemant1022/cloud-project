"""CSV import endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import require_roles
from ..logging_config import get_logger
from ..models import User
from ..schemas import ImportResult
from ..services.csv_import import TEMPLATE_CSV, import_products

logger = get_logger(__name__)
router = APIRouter(prefix="/api/import", tags=["import"])


@router.get("/template")
def download_template(
    _: User = Depends(require_roles("admin", "manager")),
) -> Response:
    logger.info("CSV template downloaded")
    return Response(
        content=TEMPLATE_CSV,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="inventory-template.csv"'},
    )


@router.post("", response_model=ImportResult)
async def upload_csv(
    file: UploadFile = File(...),
    create_missing: bool = Form(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager")),
) -> ImportResult:
    logger.info(
        "CSV upload received | filename=%s content_type=%s user=%s",
        file.filename,
        file.content_type,
        user.email,
    )
    try:
        content = await file.read()
    except Exception:
        logger.exception("Failed to read uploaded file | user=%s", user.email)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not read uploaded file") from None

    if not content:
        logger.warning("Empty CSV upload | user=%s", user.email)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    if len(content) > settings.import_max_bytes:
        logger.warning("CSV upload too large | bytes=%s user=%s", len(content), user.email)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.import_max_bytes // (1024 * 1024)} MB limit",
        )
    if file.filename and not file.filename.lower().endswith(".csv"):
        logger.warning("Non-CSV upload rejected | filename=%s", file.filename)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please upload a .csv file")

    return import_products(db, content, user, create_missing=create_missing)
