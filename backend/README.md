# Inspection Platform Backend

FastAPI backend scaffold for an automated inspection platform based on Prometheus and Elasticsearch.

## Quick start

1. Create a virtual environment and install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -e .[dev]
   ```

2. Copy `.env.example` to `.env` and update the database settings.

3. Run migrations:

   ```powershell
   alembic upgrade head
   ```

4. Start the API server:

   ```powershell
   uvicorn app.main:app --reload
   ```

## Local infrastructure

From the project root you can start PostgreSQL and Redis with Docker Compose:

```powershell
docker compose up -d postgres redis
```

The backend service definition is also included in `docker-compose.yml` if you want to run the API inside Docker.

## Current scope

- Async SQLAlchemy session management
- Datasource CRUD plus connectivity test
- Inspection rule CRUD plus version snapshots
- Manual inspection job creation plus task run materialization
- Inline execution for Prometheus and Elasticsearch inspection runs
- Alembic scaffold with initial schema migration
- Health endpoint

## Key endpoints

- `GET /api/v1/health`
- `GET|POST|PUT|DELETE /api/v1/datasources`
- `POST /api/v1/datasources/{id}/test`
- `GET|POST|PUT|DELETE /api/v1/rules`
- `POST /api/v1/rules/{id}/dry-run`
- `POST /api/v1/jobs/manual`
- `GET /api/v1/jobs`
- `GET /api/v1/jobs/{id}`
- `GET /api/v1/jobs/{id}/runs`
- `POST /api/v1/jobs/{id}/execute`
- `POST /api/v1/jobs/{id}/cancel`
- `POST /api/v1/runs/{id}/execute`
- `GET /api/v1/runs/{id}/findings`

## Threshold examples

Prometheus rule threshold example:

```json
{
  "query_config": {
    "query": "100 - (avg(rate(node_cpu_seconds_total{mode='idle'}[5m])) * 100)",
    "step": "60s"
  },
  "threshold_config": {
    "aggregation": "max",
    "operator": "gt",
    "warning": 75,
    "critical": 90,
    "suggestion": "Check host CPU saturation and hot processes."
  }
}
```

Elasticsearch rule threshold example:

```json
{
  "query_config": {
    "index": "logs-*",
    "query": {
      "bool": {
        "filter": [
          { "term": { "log.level": "error" } }
        ]
      }
    },
    "size": 0
  },
  "threshold_config": {
    "aggregation": "hits_total",
    "operator": "gt",
    "warning": 10,
    "critical": 50,
    "suggestion": "Review recent error spikes and related deployments."
  }
}
```
