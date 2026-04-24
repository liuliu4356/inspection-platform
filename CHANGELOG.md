# Changelog

All notable changes to this project will be documented in this file.

The format follows Keep a Changelog and the project uses Semantic Versioning.

## [Unreleased]

## [0.5.0] - 2026-04-25

### Added
- Celery Beat scheduler for automatic cron-based inspection execution.
- Scheduler service that evaluates cron expressions via `croniter` and
  creates inspection jobs for due rules.
- `POST /api/v1/scheduler/tick` endpoint for manual scheduler trigger.
- Beat service in Docker Compose for production deployments.
- Unit tests for croniter parsing and scheduler service logic.

### Changed
- Celery Beat configured to run `inspection.scheduler_tick` every minute.
- Routes increased to 35 (added scheduler endpoints).

## [0.4.1] - 2026-04-25

### Added
- Default admin user auto-created on startup (`admin` / `admin123`).
- Configurable default admin credentials via `DEFAULT_ADMIN_USERNAME` and
  `DEFAULT_ADMIN_PASSWORD` environment variables.
- CLI script `scripts/promote_user.py` to promote any user to a given role.

## [0.4.0] - 2026-04-25

### Added
- User authentication with JWT access and refresh tokens.
- Password hashing and verification via bcrypt.
- User registration, login, and token refresh endpoints.
- RBAC with default roles: admin, operator, viewer.
- Authentication dependency (`get_current_user`) for protected endpoints.
- Role-based access control (`require_role`) for write and execute operations.
- Automatic `created_by` / `requested_by` population from authenticated user.
- Default role seeding on application startup.
- Bilingual project documentation (English and Chinese).
- Unit tests for password hashing, JWT creation, and token lifecycle.

### Changed
- All datasource, rule, and job endpoints now require authentication.
- Write and execute operations require `operator` or `admin` role.
- Read operations require an authenticated user (`viewer` or above).

## [0.3.0] - 2026-04-25

### Added
- Celery-based asynchronous dispatch endpoints for inspection jobs and task runs.
- Worker entrypoint and Docker Compose worker service for background execution.

## [0.2.0] - 2026-04-25

### Added
- Git workflow documentation and release management conventions.
- GitHub Actions CI for backend lint and smoke validation.
- Release helper script for synchronizing repository version metadata.
- Inline inspection execution for Prometheus and Elasticsearch task runs.
- Run-level findings endpoints and threshold evaluation test coverage.

## [0.1.0] - 2026-04-25

### Added
- FastAPI backend scaffold with async SQLAlchemy session management.
- Datasource CRUD and connectivity testing for Prometheus and Elasticsearch.
- Inspection rule CRUD with version snapshots and dry-run validation.
- Manual inspection job creation and task-run materialization.
- Alembic scaffold and initial schema migration.
- Docker Compose definitions for PostgreSQL, Redis, and the API service.
