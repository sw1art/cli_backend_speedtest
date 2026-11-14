# Download Benchmark

Проект для замера скорости скачивания, реализованный двумя независимыми
частями:

1. **CLI-утилита** (`cli/`) — автономный консольный скрипт, выполняющий
   10 последовательных HTTP-запросов и выводящий среднее время, объём и
   скорость загрузки. Без инфраструктуры.
2. **Backend-сервис** (`backend/`) — расширенная реализация той же бизнес-логики
   на FastAPI + PostgreSQL (asyncpg) + RabbitMQ + Alembic, построенная по
   принципам Clean Architecture.

Обе части реализуют одну и ту же бизнес-логику (последовательные запросы,
замер времени, подсчёт байтов, расчёт скорости), но независимы друг от друга.

## Структура репозитория

```
thats_easy/
├── cli/                 # Реализация №1 (**CLI-утилита**) Консольная утилита
│   └── download_benchmark/
├── backend/             # Реализация №2 (**Backend-сервис**) FastAPI + Clean Architecture + Docker
│   ├── app/
│   │   ├── domain/        # сущности, value objects, интерфейсы репозиториев, сервисы
│   │   ├── application/   # use cases, DTO, порты (interfaces)
│   │   ├── infrastructure/# БД (SQLAlchemy/asyncpg), репозитории, httpx, RabbitMQ
│   │   ├── presentation/  # FastAPI роутеры, схемы, DI
│   │   ├── core/          # конфигурация, логирование
│   │   ├── main.py        # фабрика приложения (composition root)
│   │   └── worker.py      # отдельный процесс-воркер
│   ├── migrations/        # Alembic-миграции
│   ├── tests/
│   ├── docker-compose.yml
│   └── Dockerfile
└── README.md        
```

## Быстрый старт

- CLI: см. [`cli/README.md`](cli/README.md)
- Backend: см. [`backend/README.md`](backend/README.md)

## Краткое описание запуска

### Реализация №1 (**CLI-утилита**)

```bash
cd cli
python -m venv .venv && source .venv/bin/activate   # For Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m download_benchmark https://example.com/image.jpg
```

### Реализация №2 (**Backend-сервис**)

```bash
cd backend
cp .env.example .env
docker compose up --build
```

После запуска API доступен на `http://localhost:8000`, документация Swagger —
на `http://localhost:8000/docs`.
