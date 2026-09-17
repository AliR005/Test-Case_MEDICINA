"""Эндпоинты проверок (AGENTS.md §4).

Тонкий HTTP-слой: валидация входа, вызов сервиса, сохранение.
Бизнес-правила — только в app/services.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.enums import CheckStatus, RecordType
from app.repositories.check_repository import CheckRepository
from app.schemas.checks import (
    CheckDetailSchema,
    CheckListItemSchema,
    CheckResultSchema,
    DocumentSchema,
    ExtractedSchema,
    IssueSchema,
)
from app.services.check_service import UploadedFile, run_check

router = APIRouter(prefix="/api/checks", tags=["checks"])


def _stub_extracted(record_date_str: str) -> ExtractedSchema:
    """Заглушка извлечения (§9): полноценный разбор содержимого не требуется."""
    return ExtractedSchema(
        child_code="Р-000",
        tutor="—",
        date=record_date_str,
        observed_blocks="—",
    )


@router.post("", response_model=CheckResultSchema)
async def create_check(
    type: Annotated[RecordType, Form()],
    files: Annotated[list[UploadFile], File()],
    db: Annotated[Session, Depends(get_db)],
) -> CheckResultSchema:
    if not files:
        raise HTTPException(status_code=400, detail="Не загружено ни одного файла")

    uploaded = [
        UploadedFile(name=f.filename or "unnamed", size_bytes=len(await f.read()))
        for f in files
    ]
    result = run_check(type, uploaded)

    record_date = datetime.now(timezone.utc).date()
    check = CheckRepository(db).create(
        record_type=type,
        record_date=record_date,
        result=result,
        extracted=_stub_extracted(record_date.strftime("%d.%m.%Y")).model_dump(),
    )
    return CheckResultSchema(
        check_id=check.id,
        status=result.status,
        status_label=result.status_label,
        reason=result.reason,
        issues=[IssueSchema(level=i.level, message=i.message) for i in result.issues],
        documents=[
            DocumentSchema(
                name=d.name, detected_type=d.detected_type, size_kb=d.size_kb
            )
            for d in result.documents
        ],
        extracted=_stub_extracted(record_date.strftime("%d.%m.%Y")),
        checked_at=check.checked_at,
    )


@router.get("", response_model=list[CheckListItemSchema])
def list_checks(db: Annotated[Session, Depends(get_db)]) -> list[CheckListItemSchema]:
    checks = CheckRepository(db).list_all()
    return [
        CheckListItemSchema(
            id=c.id,
            date=c.record_date,
            record_type=c.record_type,
            status=c.status,
            documents_count=len(c.documents),
            version=c.version,
        )
        for c in checks
    ]


@router.get("/{check_id}", response_model=CheckDetailSchema)
def get_check(
    check_id: str, db: Annotated[Session, Depends(get_db)]
) -> CheckDetailSchema:
    check = CheckRepository(db).get(check_id)
    if check is None:
        raise HTTPException(status_code=404, detail="Проверка не найдена")
    status = CheckStatus(check.status)
    return CheckDetailSchema(
        check_id=check.id,
        status=status,
        status_label=check.status_label or "",
        reason=check.reason,
        issues=[IssueSchema(level=i.level, message=i.message) for i in check.issues],
        documents=[
            DocumentSchema(
                name=d.name, detected_type=d.detected_type, size_kb=d.size_kb
            )
            for d in check.documents
        ],
        extracted=ExtractedSchema(**(check.extracted or {})),
        checked_at=check.checked_at,
        record_type=check.record_type,
        record_date=check.record_date,
        version=check.version,
    )
