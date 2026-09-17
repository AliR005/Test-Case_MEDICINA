from datetime import date

from app.db.base import Base
from app.models import Check, CheckStatus, Document, Issue, IssueLevel, RecordType


def test_tables_registered() -> None:
    assert set(Base.metadata.tables) >= {"checks", "documents", "issues"}


def test_check_version_uniqueness_constraint() -> None:
    names = {c.name for c in Check.__table__.constraints if c.name}
    assert "uq_check_version" in names


def test_enum_values_match_api_contract() -> None:
    assert {m.value for m in RecordType} == {"daily", "weekly"}
    assert {m.value for m in CheckStatus} == {
        "check_in_progress",
        "complete",
        "incomplete",
    }
    assert {m.value for m in IssueLevel} == {"error", "warning"}


def test_models_instantiate_without_db() -> None:
    check = Check(record_type=RecordType.DAILY, record_date=date(2025, 3, 15), status=CheckStatus.COMPLETE)
    doc = Document(name="дневник.xlsx", size_kb=142, check=check)
    issue = Issue(level=IssueLevel.WARNING, message="unknown", check=check)
    assert check.documents == [doc]
    assert check.issues == [issue]
