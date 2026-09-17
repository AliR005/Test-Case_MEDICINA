import enum


class RecordType(str, enum.Enum):
    """Тип записи: дневная или недельная (§13: type ∈ {daily, weekly})."""

    DAILY = "daily"
    WEEKLY = "weekly"


class CheckStatus(str, enum.Enum):
    """Итоговый статус проверки (§8)."""

    CHECK_IN_PROGRESS = "check_in_progress"
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


class IssueLevel(str, enum.Enum):
    """Уровень проблемы (§13: issue.level ∈ {error, warning})."""

    ERROR = "error"
    WARNING = "warning"


class MaterialType(str, enum.Enum):
    """Тип материала, определяемый по имени файла (§5)."""

    OBSERVATION_DIARY = "observation_diary"
    LESSON_REPORT = "lesson_report"
    PARENT_FEEDBACK = "parent_feedback"
    SPECIALIST_CONCLUSION = "specialist_conclusion"
