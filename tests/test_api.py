"""API-тесты на SQLite (переопределение get_db).

Бизнес-правила покрыты в test_check_service.py без БД;
здесь — HTTP-слой: статусы, форма ответа, история версий.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture()
def client() -> Iterator[TestClient]:
    Base.metadata.create_all(engine)

    def override_db() -> Iterator[Session]:
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def _files(*names: str) -> list[tuple[str, tuple[str, bytes, str]]]:
    return [("files", (n, b"x" * 1024, "application/octet-stream")) for n in names]


FULL_DAILY = _files(
    "дневник_наблюдений.xlsx",
    "отчёт_занятие.pdf",
    "родители_фидбек.docx",
)


def test_post_complete(client: TestClient) -> None:
    resp = client.post("/api/checks", data={"type": "daily"}, files=FULL_DAILY)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "complete"
    assert body["check_id"]
    assert len(body["documents"]) == 3
    assert body["documents"][0]["detected_type"] == "observation_diary"
    assert body["documents"][0]["size_kb"] == 1
    assert body["extracted"]["child_code"]
    assert body["checked_at"]


def test_post_incomplete_missing_material(client: TestClient) -> None:
    resp = client.post(
        "/api/checks",
        data={"type": "daily"},
        files=_files("дневник.xlsx"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "incomplete"
    assert any(i["level"] == "error" for i in body["issues"])


def test_post_invalid_type_is_422(client: TestClient) -> None:
    resp = client.post(
        "/api/checks", data={"type": "monthly"}, files=FULL_DAILY
    )
    assert resp.status_code == 422


def test_list_and_detail(client: TestClient) -> None:
    created = client.post(
        "/api/checks", data={"type": "daily"}, files=FULL_DAILY
    ).json()
    listed = client.get("/api/checks").json()
    assert len(listed) == 1
    assert listed[0]["id"] == created["check_id"]
    assert listed[0]["documents_count"] == 3
    assert listed[0]["version"] == 1

    detail = client.get(f"/api/checks/{created['check_id']}").json()
    assert detail["check_id"] == created["check_id"]
    assert detail["record_type"] == "daily"
    assert len(detail["issues"]) == 0


def test_detail_404(client: TestClient) -> None:
    resp = client.get("/api/checks/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_reupload_creates_new_version(client: TestClient) -> None:
    first = client.post("/api/checks", data={"type": "daily"}, files=FULL_DAILY).json()
    second = client.post("/api/checks", data={"type": "daily"}, files=FULL_DAILY).json()
    assert first["check_id"] != second["check_id"]

    listed = client.get("/api/checks").json()
    assert len(listed) == 2
    assert sorted(i["version"] for i in listed) == [1, 2]
    # Предыдущая версия доступна.
    assert client.get(f"/api/checks/{first['check_id']}").status_code == 200
