# Inspection Platform

Automated inspection platform for Prometheus metrics and Elasticsearch logs.

## Repository layout

```text
inspection-platform/
├── backend/               # FastAPI backend
├── docs/process/          # Delivery process and versioning docs
├── scripts/               # Release helper scripts
└── .github/               # CI and collaboration templates
```

## Current status

- Backend MVP scaffold is in place.
- Datasource management, rule management, and manual job creation are available.
- Local infrastructure definitions for PostgreSQL and Redis are included.
- Git workflow, changelog, and release conventions are documented in this repository.

## Quick start

1. Start local infrastructure if Docker is available:

   ```powershell
   docker compose up -d postgres redis
   ```

2. Start the backend:

   ```powershell
   Set-Location backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -e .[dev]
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

3. Open the API docs:

   `http://127.0.0.1:8000/docs`

## Working agreements

- Development process: [docs/process/development-workflow.md](docs/process/development-workflow.md)
- Versioning policy: [docs/process/versioning.md](docs/process/versioning.md)
- Change history: [CHANGELOG.md](CHANGELOG.md)
