import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import IssueLevel


class Issue(Base):
    """Ошибка или предупреждение проверки (§10-11)."""

    __tablename__ = "issues"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    check_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("checks.id", ondelete="CASCADE"), nullable=False
    )
    level: Mapped[IssueLevel] = mapped_column(
        sa.Enum(IssueLevel, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(sa.Text, nullable=False)

    check: Mapped["Check"] = relationship(back_populates="issues")
