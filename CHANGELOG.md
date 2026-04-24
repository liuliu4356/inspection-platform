# Changelog

All notable changes to this project will be documented in this file.

The format follows Keep a Changelog and the project uses Semantic Versioning.

## [Unreleased]

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
