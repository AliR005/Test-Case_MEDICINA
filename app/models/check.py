import uuid
from datetime import date, datetime, timezone

import sqlalchemy as sa
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import CheckStatus, RecordType

_ENUM_VALUES = lambda e: [m.value for m in e]  # хранить value ('daily'), а не NAME


class Check(Base):
    """Одна проверка записи.

    Каждая загрузка — новая строка (append-only, §10):
    повторная загрузка за ту же дату создаёт новую версию,
    предыдущие версии не перезаписываются.
    """

    __tablename__ = "checks"
    __table_args__ = (
        UniqueConstraint("record_type", "record_date", "version", name="uq_check_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    record_type: Mapped[RecordType] = mapped_column(
        sa.Enum(RecordType, native_enum=False, values_callable=_ENUM_VALUES),
        nullable=False,
    )
    record_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    version: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=1)
    status: Mapped[CheckStatus] = mapped_column(
        sa.Enum(CheckStatus, native_enum=False, values_callable=_ENUM_VALUES),
        nullable=False,
    )
    status_label: Mapped[str | None] = mapped_column(sa.String(255))
    reason: Mapped[str | None] = mapped_column(sa.Text)
    extracted: Mapped[dict | None] = mapped_column(sa.JSON)
    checked_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    documents: Mapped[list["Document"]] = relationship(
        back_populates="check", cascade="all, delete-orphan"
    )
    issues: Mapped[list["Issue"]] = relationship(
        back_populates="check", cascade="all, delete-orphan"
    )
