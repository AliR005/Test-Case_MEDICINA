"""Тесты бизнес-логики (AGENTS.md §15): детекция, файлы, статусы."""

from app.models.enums import CheckStatus, IssueLevel, MaterialType, RecordType
from app.services.check_service import (
    MAX_FILE_SIZE,
    UploadedFile,
    kb_to_bytes,
    run_check,
)
from app.services.material_detection import detect_material_type


def _full_daily(extra: list[UploadedFile] | None = None) -> list[UploadedFile]:
    base = [
        UploadedFile("дневник_наблюдений_15-03.xlsx", 142 * 1024),
        UploadedFile("отчёт_о_занятии.pdf", 200 * 1024),
        UploadedFile("обратная_связь_родителя.docx", 50 * 1024),
    ]
    return base + (extra or [])


# §15.1-4: определение типов материалов.
def test_detect_observation_diary() -> None:
    assert detect_material_type("дневник_наблюдений_15-03.xlsx") == MaterialType.OBSERVATION_DIARY
    assert detect_material_type("observation_diary_mar.pdf") == MaterialType.OBSERVATION_DIARY


def test_detect_lesson_report() -> None:
    assert detect_material_type("отчёт_о_занятии.pdf") == MaterialType.LESSON_REPORT
    assert detect_material_type("lesson_report_12.docx") == MaterialType.LESSON_REPORT


def test_detect_parent_feedback() -> None:
    assert detect_material_type("обратная_связь_родителя.docx") == MaterialType.PARENT_FEEDBACK
    assert detect_material_type("parent_feedback.jpg") == MaterialType.PARENT_FEEDBACK


def test_detect_specialist_conclusion() -> None:
    assert detect_material_type("заключение_специалиста.pdf") == MaterialType.SPECIALIST_CONCLUSION
    assert detect_material_type("specialist_conclusion.pdf") == MaterialType.SPECIALIST_CONCLUSION


# §15.5: неизвестное имя → warning, остальные файлы проверяются.
def test_unknown_filename_is_warning() -> None:
    result = run_check(RecordType.DAILY, _full_daily([UploadedFile("scan_0041.jpg", 80 * 1024)]))
    assert result.status == CheckStatus.COMPLETE
    warnings = [i for i in result.issues if i.level == IssueLevel.WARNING]
    assert len(warnings) == 1
    assert "scan_0041.jpg" in warnings[0].message
    assert not any(i.level == IssueLevel.ERROR for i in result.issues)


# §15.6: корректный complete.
def test_complete_daily() -> None:
    result = run_check(RecordType.DAILY, _full_daily())
    assert result.status == CheckStatus.COMPLETE
    assert result.issues == []
    assert result.reason is None


def test_complete_weekly_requires_specialist() -> None:
    result = run_check(
        RecordType.WEEKLY,
        _full_daily([UploadedFile("заключение_специалиста.pdf", 100 * 1024)]),
    )
    assert result.status == CheckStatus.COMPLETE


# §15.7: incomplete при отсутствии обязательного материала.
def test_incomplete_on_missing_material() -> None:
    result = run_check(RecordType.DAILY, [UploadedFile("дневник.xlsx", 100 * 1024)])
    assert result.status == CheckStatus.INCOMPLETE
    errors = [i for i in result.issues if i.level == IssueLevel.ERROR]
    assert any("обратная связь родителя" in e.message for e in errors)
    assert result.reason is not None


def test_weekly_without_specialist_is_incomplete() -> None:
    result = run_check(RecordType.WEEKLY, _full_daily())
    assert result.status == CheckStatus.INCOMPLETE
    assert any("заключение специалиста" in i.message for i in result.issues)


# §15.8: недопустимый формат → error.
def test_invalid_format_is_error() -> None:
    result = run_check(
        RecordType.DAILY, _full_daily([UploadedFile("заметки.txt", 1024)])
    )
    assert result.status == CheckStatus.INCOMPLETE
    assert any("Недопустимый формат" in i.message for i in result.issues)


# §15.9: файл больше 20 МБ → error.
def test_oversize_file_is_error() -> None:
    big = UploadedFile("дневник_наблюдений.xlsx", MAX_FILE_SIZE + 1)
    result = run_check(RecordType.DAILY, [big])
    assert any("20 МБ" in i.message for i in result.issues)


def test_exactly_20mb_passes_size_check() -> None:
    files = _full_daily()
    files[0] = UploadedFile(files[0].name, MAX_FILE_SIZE)
    result = run_check(RecordType.DAILY, files)
    assert not any("20 МБ" in i.message for i in result.issues)


def test_kb_to_bytes() -> None:
    assert kb_to_bytes(142) == 142 * 1024
