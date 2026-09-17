"""Слой сохранения проверок (AGENTS.md §10-11).

Каждая загрузка — новая строка в checks (append-only):
версия = max(version) + 1 для пары (record_type, record_date).
"""

from datetime import date
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Session, joinedload

from app.models.check import Check
from app.models.document import Document
from app.models.enums import RecordType
from app.models.issue import Issue
from app.services.check_service import CheckResult


class CheckRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def next_version(self, record_type: RecordType, record_date: date) -> int:
        current = self.db.scalar(
            sa.select(sa.func.max(Check.version)).where(
                Check.record_type == record_type,
                Check.record_date == record_date,
            )
        )
        return (current or 0) + 1

    def create(
        self,
        record_type: RecordType,
        record_date: date,
        result: CheckResult,
        extracted: dict,
    ) -> Check:
        check = Check(
            record_type=record_type,
            record_date=record_date,
            version=self.next_version(record_type, record_date),
            status=result.status,
            status_label=result.status_label,
            reason=result.reason,
            extracted=extracted,
            documents=[
                Document(
                    name=d.name,
                    detected_type=d.detected_type,
                    size_kb=d.size_kb,
                    file_format=d.file_format,
                )
                for d in result.documents
            ],
            issues=[Issue(level=i.level, message=i.message) for i in result.issues],
        )
        self.db.add(check)
        self.db.commit()
        self.db.refresh(check)
        return check

    def list_all(self) -> list[Check]:
        return list(
            self.db.scalars(
                sa.select(Check)
                .options(joinedload(Check.documents), joinedload(Check.issues))
                .order_by(Check.checked_at.desc(), Check.record_date.desc())
            )
            .unique()
            .all()
        )

    def get(self, check_id: str) -> Check | None:
        try:
            key = uuid.UUID(str(check_id))
        except ValueError:
            return None
        return self.db.scalar(
            sa.select(Check)
            .options(joinedload(Check.documents), joinedload(Check.issues))
            .where(Check.id == key)
        )
