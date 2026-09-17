"""Проверка записи: файлы, комплектность, итоговый статус (§6-8).

Чистая бизнес-логика: на вход — тип записи и файлы,
на выходе — результат с issues и статусом. Без HTTP и БД.
"""

import math
import os
from dataclasses import dataclass, field

from app.models.enums import CheckStatus, IssueLevel, MaterialType, RecordType
from app.services.material_detection import MATERIAL_LABELS, detect_material_type

ALLOWED_FORMATS = ("pdf", "docx", "xlsx", "jpg", "jpeg", "png")
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 МБ (§7)

REQUIRED_MATERIALS: dict[RecordType, tuple[MaterialType, ...]] = {
    RecordType.DAILY: (
        MaterialType.OBSERVATION_DIARY,
        MaterialType.LESSON_REPORT,
        MaterialType.PARENT_FEEDBACK,
    ),
    RecordType.WEEKLY: (
        MaterialType.OBSERVATION_DIARY,
        MaterialType.LESSON_REPORT,
        MaterialType.PARENT_FEEDBACK,
        MaterialType.SPECIALIST_CONCLUSION,
    ),
}

STATUS_LABELS: dict[CheckStatus, str] = {
    CheckStatus.COMPLETE: "Запись полная — можно передавать в анализ",
    CheckStatus.INCOMPLETE: "Запись неполная — нельзя передавать в анализ",
    CheckStatus.CHECK_IN_PROGRESS: "Проверка выполняется",
}


@dataclass
class UploadedFile:
    name: str
    size_bytes: int


@dataclass
class CheckedDocument:
    name: str
    detected_type: MaterialType | None
    size_kb: int
    file_format: str


@dataclass
class CheckIssue:
    level: IssueLevel
    message: str


@dataclass
class CheckResult:
    status: CheckStatus
    status_label: str
    reason: str | None
    issues: list[CheckIssue] = field(default_factory=list)
    documents: list[CheckedDocument] = field(default_factory=list)


def check_file_format(name: str) -> CheckIssue | None:
    """Недопустимый формат → error (§7)."""
    ext = os.path.splitext(name.lower())[1].lstrip(".")
    if ext not in ALLOWED_FORMATS:
        return CheckIssue(
            IssueLevel.ERROR,
            f"Недопустимый формат файла: «{name}». "
            "Разрешены: PDF, DOCX, XLSX, JPG, PNG",
        )
    return None


def check_file_size(file: UploadedFile) -> CheckIssue | None:
    """Файл больше 20 МБ → error (§7)."""
    if file.size_bytes > MAX_FILE_SIZE:
        return CheckIssue(
            IssueLevel.ERROR,
            f"Файл «{file.name}» превышает максимальный размер 20 МБ",
        )
    return None


def run_check(record_type: RecordType, files: list[UploadedFile]) -> CheckResult:
    """Выполнить проверку записи (§4, п.1-6)."""
    issues: list[CheckIssue] = []
    documents: list[CheckedDocument] = []

    for file in files:
        # Формат и размер проверяются независимо для каждого файла (§7).
        if (issue := check_file_format(file.name)) is not None:
            issues.append(issue)
        if (issue := check_file_size(file)) is not None:
            issues.append(issue)

        detected = detect_material_type(file.name)
        if detected is None:
            # Неизвестный материал — warning, проверка остальных продолжается (§5).
            issues.append(
                CheckIssue(
                    IssueLevel.WARNING,
                    f"Не удалось определить тип материала: «{file.name}»",
                )
            )

        ext = os.path.splitext(file.name.lower())[1].lstrip(".")
        documents.append(
            CheckedDocument(
                name=file.name,
                detected_type=detected,
                size_kb=int(round(file.size_bytes / 1024)),
                file_format=ext,
            )
        )

    # Комплектность: отсутствие обязательного материала → error (§6).
    found = {d.detected_type for d in documents if d.detected_type is not None}
    for required in REQUIRED_MATERIALS[record_type]:
        if required not in found:
            issues.append(
                CheckIssue(
                    IssueLevel.ERROR,
                    f"Отсутствует обязательный материал: {MATERIAL_LABELS[required]}",
                )
            )

    # Итоговый статус: warnings не делают запись incomplete (§8).
    errors = [i.message for i in issues if i.level == IssueLevel.ERROR]
    status = CheckStatus.INCOMPLETE if errors else CheckStatus.COMPLETE
    return CheckResult(
        status=status,
        status_label=STATUS_LABELS[status],
        reason="; ".join(errors) if errors else None,
        issues=issues,
        documents=documents,
    )


def kb_to_bytes(size_kb: float) -> int:
    return math.ceil(size_kb * 1024)
