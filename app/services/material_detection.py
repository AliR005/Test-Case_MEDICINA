"""Определение типа материала по имени файла (AGENTS.md §5).

Чистая бизнес-логика: без HTTP и БД, покрывается unit-тестами.
Неизвестное имя — не ошибка, а None (caller добавит warning).
"""

import os

from app.models.enums import MaterialType

# Подстроки-маркеры (нижний регистр): кириллица + латиница + транслит.
_PATTERNS: dict[MaterialType, tuple[str, ...]] = {
    MaterialType.OBSERVATION_DIARY: (
        "дневник",
        "dnevnik",
        "наблюден",
        "nablyud",
        "observ",
        "diary",
    ),
    MaterialType.LESSON_REPORT: (
        "заняти",
        "zanyati",
        "урок",
        "urok",
        "lesson",
        "отчёт о занятии",
        "отчет о занятии",
    ),
    MaterialType.PARENT_FEEDBACK: (
        "родител",
        "roditel",
        "parent",
        "feedback",
        "отзыв",
        "otzyv",
        "обратн",
    ),
    MaterialType.SPECIALIST_CONCLUSION: (
        "специалист",
        "specialist",
        "заключен",
        "zaklyuchen",
        "conclusion",
    ),
}

# Русские названия для сообщений об отсутствии материала (§6).
MATERIAL_LABELS: dict[MaterialType, str] = {
    MaterialType.OBSERVATION_DIARY: "дневник наблюдений",
    MaterialType.LESSON_REPORT: "отчёт о занятии",
    MaterialType.PARENT_FEEDBACK: "обратная связь родителя",
    MaterialType.SPECIALIST_CONCLUSION: "заключение специалиста",
}


def detect_material_type(filename: str) -> MaterialType | None:
    """Определить тип по имени файла (без расширения).

    Побеждает тип с наибольшим числом совпадений;
    ни одного совпадения — None (неизвестный материал).
    """
    stem, _ = os.path.splitext(filename.lower())
    best: MaterialType | None = None
    best_hits = 0
    for material_type, patterns in _PATTERNS.items():
        hits = sum(1 for p in patterns if p in stem)
        if hits > best_hits:
            best, best_hits = material_type, hits
    return best
