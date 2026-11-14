# Download Benchmark Backend

Расширенная реализация задачи замера скорости скачивания в виде асинхронного
REST-сервиса на **FastAPI** с **PostgreSQL (asyncpg)**, **RabbitMQ** и
**Alembic**, построенного по принципам **Clean Architecture**.

## Архитектура

Проект разделён на независимые слои. Зависимости направлены внутрь:
`presentation → application → domain`, а `infrastructure` реализует интерфейсы
(порты), объявленные в `domain` и `application`. Слои `domain` и `application`
**не зависят** от FastAPI, PostgreSQL, RabbitMQ или конкретных библиотек.

```
┌────────────────────────────────────────────────────────────┐
│                        presentation                        │
│         FastAPI routers · Pydantic schemas · DI             │
└──────────────────────────────┬─────────────────────────────┘
                               │ use cases, DTO
┌──────────────────────────────▼─────────────────────────────┐
│                        application                         │
│  use cases · DTO · interfaces (HttpClient, MessagePublisher)│
└───────────────┬──────────────────────────────┬─────────────┘
                │ repositories (port)          │ ports
┌───────────────▼───────────────┐  ┌───────────▼─────────────┐
│            domain             │  │      infrastructure     │
│  entities · value objects     │  │  SQLAlchemy+asyncpg     │
│  repositories (abstract)      │◄─┤  httpx · aio-pika       │
│  services (pure rules)        │  │  Alembic                │
└───────────────────────────────┘  └─────────────────────────┘
```

Взаимодействие компонентов:

```
        POST /api/v1/tasks
Client ─────────────────────▶ API (FastAPI)
                              │  1. валидация URL
                              │  2. INSERT в PostgreSQL (PENDING)
                              │  3. publish в RabbitMQ
                              ▼
                       ┌─────────────┐         ┌──────────────┐
                       │  RabbitMQ   │───────▶│    Worker    │
                       │  queue      │ consume │  (отдельный  │
                       └─────────────┘         │   процесс)   │
                                               │  10 запросов │
                                               │  httpx async │
                                               │ → PostgreSQL │
                                               └──────────────┘
```

### Структура

```
backend/
├── app/
│   ├── domain/                 # ядро (без внешних зависимостей)
│   │   ├── entities/           # DownloadTask (агрегат + машина состояний)
│   │   ├── value_objects/      # TaskStatus, RequestResult, BenchmarkSummary
│   │   ├── repositories/       # интерфейс DownloadTaskRepository
│   │   └── services/           # чистые правила (валидация URL, статистика)
│   ├── application/
│   │   ├── use_cases/          # Create/Get/Execute/... DownloadTask
│   │   ├── dto/                # объекты передачи данных
│   │   └── interfaces/         # порты HttpClient, MessagePublisher
│   ├── infrastructure/
│   │   ├── database/           # SQLAlchemy Async, модели
│   │   ├── repositories/       # SQLAlchemyTaskRepository
│   │   ├── http_client/        # httpx.AsyncClient
│   │   └── messaging/          # aio-pika (publish + retry queue)
│   ├── presentation/
│   │   ├── api/                # роутеры /tasks, /health
│   │   ├── schemas/            # Pydantic-схемы
│   │   └── dependencies.py     # DI-провайдеры
│   ├── core/                   # config (pydantic-settings), logging
│   ├── main.py                 # фабрика приложения (composition root)
│   └── worker.py               # воркер (отдельный процесс)
├── migrations/                 # Alembic
├── tests/
├── docker-compose.yml
├── Dockerfile
└── .env.example
```

### Бизнес-правила (domain)

Статусы задачи: `PENDING → PROCESSING → COMPLETED | FAILED`.

- `PENDING` — задача создана и поставлена в очередь.
- `PROCESSING` — воркер взял задачу в работу.
- `COMPLETED` — измерения выполнены, есть хотя бы один успешный запрос.
- `FAILED` — все запросы провалились, либо задача упала после исчерпания повторов.

Статистика (`BenchmarkSummary`) считается только по успешным (2xx) запросам:
среднее время, суммарный объём байтов и средняя скорость
(байт/сек). Смена статусов контролируется в сущности `DownloadTask` и запрещает
нелегальные переходы.

## Запуск через Docker Compose

```bash
cd backend
cp .env.example .env          # при необходимости поменяйте пароли/порты
docker compose up --build
```

Состав контейнеров:

| Контейнер | Назначение |
|-----------|------------|
| `api`     | FastAPI-приложение (uvicorn) на `:8000` |
| `worker`  | Обработка задач из RabbitMQ |
| `postgres`| Хранение данных (`:5432`) |
| `rabbitmq`| Очередь задач (`:5672`, management `:15672`) |
| `migrate` | Одноразовое применение миграций Alembic |

После старта:

- API: <http://localhost:8000>
- Swagger/OpenAPI: <http://localhost:8000/docs>
- RabbitMQ Management: <http://localhost:15672> (`guest`/`guest`)

## Переменные окружения

См. [`.env.example`](.env.example). Основные:

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `DATABASE_URL` | DSN PostgreSQL (asyncpg) | `postgresql+asyncpg://...` |
| `RABBITMQ_URL` | DSN RabbitMQ (amqp) | `amqp://guest:guest@...` |
| `RABBITMQ_QUEUE` | Основная очередь | `download_tasks` |
| `RABBITMQ_RETRY_QUEUE` | Очередь повторов (DLX) | `download_tasks.retry` |
| `MAX_RETRIES` | Максимум повторов обработки | `3` |
| `RETRY_DELAY_MS` | База задержки повтора (умножается на номер) | `2000` |
| `HTTP_TIMEOUT` | Таймаут одного запроса, сек | `30.0` |
| `SSRF_GUARD_ENABLED` | Включить SSRF-защиту | `true` |
| `SSRF_ALLOW_PRIVATE` | Разрешить private/loopback-адреса (для локальной разработки) | `false` |
| `SSRF_ALLOWED_HOSTS` | Хосты, которые всегда разрешены (через запятую) | пусто |

## REST API

| Метод | Endpoint | Назначение |
|-------|----------|------------|
| `POST` | `/api/v1/tasks` | Создание задачи |
| `GET`  | `/api/v1/tasks/{id}` | Статус задачи |
| `GET`  | `/api/v1/tasks/{id}/results` | Результаты измерений |
| `GET`  | `/api/v1/tasks` | Список задач (пагинация) |
| `GET`  | `/health` | Liveness-проверка |
| `GET`  | `/health/ready` | Readiness (проверка БД и брокера) |
| `GET`  | `/metrics` | Prometheus-метрики |

### Примеры запросов

Создание задачи:

```bash
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/image.jpg", "total_requests": 10}'
```

Ответ:

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "url": "https://example.com/image.jpg",
  "status": "PENDING",
  "total_requests": 10,
  "created_at": "2026-11-14T11:00:00Z",
  "started_at": null,
  "finished_at": null,
  "error_message": null,
  "summary": null,
  "results": []
}
```

Получение статуса:

```bash
curl http://localhost:8000/api/v1/tasks/{uuid}
```

Получение результатов:

```bash
curl http://localhost:8000/api/v1/tasks/{uuid}/results
```

## Структура БД

Таблица `download_tasks`:

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | UUID PK | Идентификатор задачи |
| `url` | varchar(2048) | Целевой URL |
| `status` | varchar(32) | `PENDING/PROCESSING/COMPLETED/FAILED` |
| `total_requests` | integer | Число запросов |
| `created_at` / `started_at` / `finished_at` | timestamptz | Временные метки |
| `error_message` | text | Ошибка (для FAILED) |

Таблица `request_results` (один-ко-многим к `download_tasks`):

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | bigint PK | — |
| `task_id` | UUID FK | Ссылка на задачу (CASCADE) |
| `request_index` | integer | Номер запроса (1..N) |
| `elapsed_seconds` | float | Время запроса |
| `bytes_downloaded` | bigint | Объём данных |
| `status_code` | integer | HTTP-статус |
| `success` | boolean | Успешен ли запрос (2xx) |
| `error_message` | text | Ошибка (если есть) |

## Безопасность (SSRF)

Воркер качает URL, переданный клиентом, поэтому включена защита от SSRF:
при создании задачи (и повторно в воркере перед скачиванием) URL проверяется на
`http/https`, а его хост — на то, что он разрешается в **глобально
маршрутизируемый** адрес. Private/loopback/link-local/резервированные адреса
(например, `127.0.0.1`, `169.254.169.254`, `10.0.0.0/8`) отклоняются.

Для локальной разработки можно:

- разрешить приватные адреса: `SSRF_ALLOW_PRIVATE=true`;
- или разрешить конкретные хосты: `SSRF_ALLOWED_HOSTS=api,host.docker.internal`.

## Метрики

Эндпоинт `/metrics` отдаёт Prometheus-метрики: счётчик `http_requests_total`
и гистограмму `http_request_duration_seconds` (по шаблону маршрута, без
кардинальности от UUID), а также счётчики `download_tasks_created_total`,
`download_tasks_completed_total`, `download_tasks_failed_total`.

## Обработка задач и Retry

1. API публикует `{"task_id": ..., "retry_count": 0}` в durable-очередь.
2. Worker (с `prefetch_count=1`) получает сообщение, ставит задачу в
   `PROCESSING`, выполняет 10 последовательных запросов через
   `httpx.AsyncClient`, сохраняет результаты и ставит `COMPLETED`/`FAILED`,
   затем `ACK`.
3. При ошибке сообщение публикуется в retry-очередь с TTL и заголовком
   `x-retry-count`; по истечении TTL оно через dead-letter exchange
   возвращается в основную очередь (экспоненциальная задержка). После
   `MAX_RETRIES` задача помечается `FAILED`, сообщение снимается.

## Локальная разработка и тесты

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

# применить миграции к локальной БД (или использовать docker compose up)
alembic upgrade head

# запустить API
uvicorn app.main:app --reload

# запустить воркер (в другом терминале)
python -m app.worker

# запустить тесты
pytest
```

Тесты покрывают:

- **unit** — расчёт статистики, смена статусов, валидация URL;
- **application** — use cases на in-memory фейках;
- **integration** — репозиторий на SQLite (aiosqlite), HTTP-клиент на
  `httpx.MockTransport`;
- **API** — создание/получение задач, валидация, 404, список, результаты.

Полноценная интеграция с PostgreSQL и RabbitMQ проверяется через Docker
Compose (`migrate` + healthcheck-и + обработка задачи воркером).
