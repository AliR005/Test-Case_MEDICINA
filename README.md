# Med checks — проверка записей наблюдений за детьми

Backend-сервис проверки дневных (`daily`) и недельных (`weekly`) записей наблюдений:
принимает материалы, определяет их тип по имени файла, проверяет комплектность,
формат и размер, формирует итоговый статус и сохраняет результат с историей версий в PostgreSQL.

## Запуск

```bash
cp .env.example .env   # опционально: есть дефолты
docker compose up --build
```

API: `http://localhost:8000`, docs: `http://localhost:8000/docs`.
Приложение ждёт healthy Postgres (`depends_on: service_healthy`).

## Тесты

```bash
uv sync
uv run pytest
```

Бизнес-логика (`tests/test_check_service.py`, 13 кейсов: все 9 правил из ТЗ) — без БД.
API-тесты (`tests/test_api.py`, 6 кейсов: статусы, форма ответа, 404, версионность) — на SQLite через переопределение `get_db`, Postgres не нужен.

## Миграции

```bash
export DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/med_checks"
uv run alembic upgrade head        # применить
uv run alembic revision --autogenerate -m "..."  # новая ревизия после изменения моделей
```

Схема меняется только миграциями; `create_all` при старте не используется.

## Технологии

| Технология | Почему |
|---|---|
| Python 3.11 | Требование ТЗ; `uv` ставит его сам (`.python-version`) |
| FastAPI | Требование ТЗ; multipart + автодокументация OpenAPI |
| PostgreSQL | Требование ТЗ; история версий, JSONB→JSON, UUID |
| SQLAlchemy 2.0 | Требование ТЗ; `Mapped`/`mapped_column`, миграции через Alembic |
| Pydantic v2 | Требование ТЗ; валидация `type`/`status`/`level` как enum, response-схемы |
| Alembic | Требование ТЗ; версионирование схемы (`alembic/versions`) |
| pytest | Требование ТЗ; 24 теста, БД не требуется |
| Docker / Compose | Требование ТЗ; `docker compose up` поднимает `app` + `postgres` |
| uv | Один инструмент вместо pip/venv: `pyproject.toml` + `uv.lock`, воспроизводимые сборки (`uv sync --frozen` и в Docker) |

## Архитектура

```text
app/
├── main.py            # фабрика FastAPI, /health, подключение роутера
├── api/checks.py      # тонкий HTTP-слой: POST/GET /api/checks
├── schemas/checks.py  # Pydantic response-схемы
├── services/
│   ├── material_detection.py  # тип материала по имени файла
│   └── check_service.py       # формат/размер/комплектность/статус
├── repositories/check_repository.py  # персистентность + next_version
├── models/            # Check / Document / Issue / enums (SQLAlchemy)
├── db/                # Base, engine/session, get_db
└── core/config.py     # настройки из env
```

Поток `POST /api/checks`: multipart (`type` + файлы) → чтение файлов в память →
`run_check()` (чистая функция: формат/размер/детекция/комплектность/статус) →
`CheckRepository.create()` (версия = max+1 для пары тип+дата, каскадно документы и issues) →
ответ по §9 (`check_id`, `status`, `issues`, `documents`, `extracted`-заглушка, `checked_at`).

Правила (§5–8 ТЗ): неизвестное имя файла → `warning` (не `error`); отсутствие
обязательного материала / плохой формат / >20 МБ → `error`; `incomplete` при
хотя бы одном `error`, иначе `complete`. `daily` требует 3 материала,
`weekly` — 4 (включая заключение специалиста). Повторная загрузка за ту же дату
создаёт новую версию, старые доступны через `GET /api/checks/{id}`.

`extracted` — демонстрационная заглушка (разбор содержимого вне скоупа ТЗ).

## Environment

| Переменная | Назначение | Дефолт (compose) |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy-URL приложения | `postgresql+psycopg2://postgres:postgres@postgres:5432/med_checks` |
| `POSTGRES_DB` | База в контейнере Postgres | `med_checks` |
| `POSTGRES_USER` | Пользователь Postgres | `postgres` |
| `POSTGRES_PASSWORD` | Пароль Postgres | `postgres` |

Все значения в `.env.example` — демонстрационные. `.env` не коммитится.

## API

Создание проверки (multipart):

```bash
curl -X POST localhost:8000/api/checks \
  -F "type=daily" \
  -F "files=@дневник_наблюдений.xlsx" \
  -F "files=@отчёт_занятие.pdf" \
  -F "files=@родители_фидбек.docx"
```

Ответ `200`:

```json
{
  "check_id": "7c9e6679-7425-4e6b-a5f3-0f0e0e0e0e0e",
  "status": "complete",
  "status_label": "Запись полная — можно передавать в анализ",
  "reason": null,
  "issues": [],
  "documents": [
    {"name": "дневник_наблюдений.xlsx", "detected_type": "observation_diary", "size_kb": 142}
  ],
  "extracted": {"child_code": "Р-000", "tutor": "—", "date": "15.03.2025", "observed_blocks": "—"},
  "checked_at": "2025-03-15T14:32:00Z"
}
```

Список и детали:

```bash
curl localhost:8000/api/checks
curl localhost:8000/api/checks/<check_id>   # 404, если нет
```

Ошибки: `400` — пустая загрузка; `404` — проверка не найдена; `422` — невалидный `type` (допустимы `daily`/`weekly`) или отсутствие файлов.
