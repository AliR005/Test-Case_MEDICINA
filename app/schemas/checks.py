"""Response-схемы проверок (AGENTS.md §9, §13)."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import CheckStatus, IssueLevel, MaterialType, RecordType


class IssueSchema(BaseModel):
    level: IssueLevel
    message: str


class DocumentSchema(BaseModel):
    name: str
    detected_type: MaterialType | None
    size_kb: int


class ExtractedSchema(BaseModel):
    child_code: str
    tutor: str
    date: str
    observed_blocks: str


class CheckResultSchema(BaseModel):
    """Ответ POST /api/checks (§9)."""

    check_id: UUID
    status: CheckStatus
    status_label: str
    reason: str | None
    issues: list[IssueSchema]
    documents: list[DocumentSchema]
    extracted: ExtractedSchema
    checked_at: datetime


class CheckListItemSchema(BaseModel):
    """Элемент GET /api/checks (§4)."""

    id: UUID
    date: date
    record_type: RecordType
    status: CheckStatus
    documents_count: int
    version: int


class CheckDetailSchema(CheckResultSchema):
    """Ответ GET /api/checks/{id}: полный результат + метаданные версии."""

    record_type: RecordType
    record_date: date
    version: int
