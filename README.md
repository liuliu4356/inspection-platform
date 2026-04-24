# Inspection Platform

Automated inspection platform for Prometheus metrics and Elasticsearch logs.

## Architecture

```text
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Client    │────▶│  FastAPI (Async) │────▶│   PostgreSQL     │
└─────────────┘     │   + Celery       │     └──────────────────┘
                    │   (Background)   │     ┌──────────────────┐
                    └──────────────────┘────▶│      Redis       │
                                             └──────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI (Python 3.11+) |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 |
| Async Queue | Celery + Redis |
| Auth | JWT (access + refresh tokens), bcrypt |
| Datasources | Prometheus, Elasticsearch |

## Modules

| Module | Status | Version |
|--------|--------|---------|
| Datasource CRUD + connectivity | ✅ Done | 0.1.0 |
| Inspection rule CRUD + versions | ✅ Done | 0.1.0 |
| Job creation + execution engine | ✅ Done | 0.2.0 |
| Async dispatch (Celery) | ✅ Done | 0.3.0 |
| **User authentication + RBAC** | ✅ **Done** | **0.4.0** |
| **Scheduled tasks (Celery Beat)** | ✅ **Done** | **0.5.0** |
| Report generation | 📋 Planned | - |
| Alerting / notifications | 📋 Planned | - |
| Frontend | 📋 Planned | - |

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (for PostgreSQL and Redis)
- pip

### 1. Start local infrastructure

```powershell
docker compose up -d postgres redis
```

### 2. Setup backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

### 3. Configure environment

```powershell
cp .env.example .env
# Edit .env if needed, especially SECRET_KEY for production
```

### 4. Run migrations

```powershell
alembic upgrade head
```

### 5. Start server

```powershell
uvicorn app.main:app --reload
```

### 6. Open API docs

[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## API Overview

### Authentication (v0.4.0)

All API endpoints except `/auth/*`, `/health`, and `/` require authentication.

| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| POST | `/api/v1/auth/register` | Register new user | Public |
| POST | `/api/v1/auth/login` | Login, get JWT pair | Public |
| POST | `/api/v1/auth/refresh` | Refresh tokens | Public |
| GET | `/api/v1/auth/me` | Current user info | Authenticated |

**Default roles**: `admin`, `operator`, `viewer` (new users get `viewer` by default)

| Role | Read | Write | Execute | Admin |
|------|------|-------|---------|-------|
| admin | ✅ | ✅ | ✅ | ✅ |
| operator | ✅ | ✅ | ✅ | - |
| viewer | ✅ | - | - | - |

### Datasources

| Method | Endpoint | Min Role |
|--------|----------|----------|
| GET | `/api/v1/datasources` | viewer |
| POST | `/api/v1/datasources` | operator |
| GET | `/api/v1/datasources/{id}` | viewer |
| PUT | `/api/v1/datasources/{id}` | operator |
| DELETE | `/api/v1/datasources/{id}` | operator |
| POST | `/api/v1/datasources/{id}/test` | operator |

### Rules

| Method | Endpoint | Min Role |
|--------|----------|----------|
| GET | `/api/v1/rules` | viewer |
| POST | `/api/v1/rules` | operator |
| GET | `/api/v1/rules/{id}` | viewer |
| PUT | `/api/v1/rules/{id}` | operator |
| DELETE | `/api/v1/rules/{id}` | operator |
| GET | `/api/v1/rules/{id}/versions` | viewer |
| POST | `/api/v1/rules/{id}/dry-run` | operator |

### Jobs & Runs

| Method | Endpoint | Min Role |
|--------|----------|----------|
| POST | `/api/v1/jobs/manual` | operator |
| GET | `/api/v1/jobs` | viewer |
| GET | `/api/v1/jobs/{id}` | viewer |
| GET | `/api/v1/jobs/{id}/runs` | viewer |
| POST | `/api/v1/jobs/{id}/cancel` | operator |
| POST | `/api/v1/jobs/{id}/execute` | operator |
| POST | `/api/v1/jobs/{id}/dispatch` | operator |
| GET | `/api/v1/runs/{id}` | viewer |
| POST | `/api/v1/runs/{id}/execute` | operator |
| POST | `/api/v1/runs/{id}/dispatch` | operator |
| GET | `/api/v1/runs/{id}/findings` | viewer |

### Scheduler (v0.5.0)

| Method | Endpoint | Description | Min Role |
|--------|----------|-------------|----------|
| POST | `/api/v1/scheduler/tick` | Manually trigger scheduler check | operator |

The scheduler runs automatically every minute via Celery Beat. It checks all
enabled rules with `schedule_type=cron` and creates inspection jobs when their
cron expression matches the current time window.

### Health

| Method | Endpoint |
|--------|----------|
| GET | `/api/v1/health` |
| GET | `/` |

## Execution Modes

- **`execute`**: Runs inspection immediately in the API process.
- **`dispatch`**: Enqueues the work through Celery for background execution.
- Set `CELERY_TASK_ALWAYS_EAGER=true` to run Celery tasks locally for development.

## Repository Layout

```text
inspection-platform/
├── backend/               # FastAPI backend
│   ├── app/               # Application code
│   │   ├── api/           # API endpoints
│   │   ├── core/          # Config, security, crypto
│   │   ├── db/            # Database session
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   └── tasks/         # Celery tasks
│   ├── tests/             # Test suite
│   └── alembic/           # Migrations
├── docs/process/          # Development process docs
├── scripts/               # Release scripts
└── .github/               # CI configuration
```

## Working Agreements

- [Development Workflow](docs/process/development-workflow.md)
- [Versioning Policy](docs/process/versioning.md)
- [Change History](CHANGELOG.md)
