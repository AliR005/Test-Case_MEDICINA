import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import MaterialType


class Document(Base):
    """Загруженный материал проверки (§10-11)."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    check_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("checks.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    detected_type: Mapped[MaterialType | None] = mapped_column(
        sa.Enum(MaterialType, native_enum=False, values_callable=lambda e: [m.value for m in e])
    )
    size_kb: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    file_format: Mapped[str | None] = mapped_column(sa.String(16))

    check: Mapped["Check"] = relationship(back_populates="documents")
