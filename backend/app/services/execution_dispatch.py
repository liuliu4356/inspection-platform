from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.models.enums import JobStatus
from app.services.job_service import execute_job, execute_run, get_job_or_404, get_run_or_404
from app.tasks.execution import execute_job_task, execute_run_task

settings = get_settings()


@dataclass(slots=True)
class DispatchResult:
    entity_type: str
    entity_id: UUID
    task_id: str
    queued_at: datetime
    execution_mode: str
    queue: str


def build_dispatch_record(*, task_id: str, queue: str, execution_mode: str) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "queue": queue,
        "execution_mode": execution_mode,
        "queued_at": datetime.now(UTC).isoformat(),
    }


def _next_eager_task_id(prefix: str) -> str:
    return f"{prefix}-eager-{uuid4().hex[:12]}"


async def dispatch_job_execution(session, job_id: UUID) -> DispatchResult:
    job = await get_job_or_404(session, job_id)
    if job.status == JobStatus.cancelled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cancelled jobs cannot be dispatched")

    async_mode = "eager" if settings.celery_task_always_eager else "queued"
    queued_at = datetime.now(UTC)
    if settings.celery_task_always_eager:
        task_id = _next_eager_task_id("job")
    else:
        celery_result = execute_job_task.apply_async(
            args=[str(job.id)],
            queue=settings.celery_task_default_queue,
        )
        task_id = celery_result.id

    summary = dict(job.summary_json)
    summary["dispatch"] = build_dispatch_record(
        task_id=task_id,
        queue=settings.celery_task_default_queue,
        execution_mode=async_mode,
    )
    job.summary_json = summary
    await session.commit()
    if settings.celery_task_always_eager:
        await execute_job(session, job.id)
    return DispatchResult(
        entity_type="job",
        entity_id=job.id,
        task_id=task_id,
        queued_at=queued_at,
        execution_mode=async_mode,
        queue=settings.celery_task_default_queue,
    )


async def dispatch_run_execution(session, run_id: UUID) -> DispatchResult:
    run = await get_run_or_404(session, run_id)
    if run.status == JobStatus.cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cancelled task runs cannot be dispatched",
        )

    async_mode = "eager" if settings.celery_task_always_eager else "queued"
    queued_at = datetime.now(UTC)
    if settings.celery_task_always_eager:
        task_id = _next_eager_task_id("run")
    else:
        celery_result = execute_run_task.apply_async(
            args=[str(run.id)],
            queue=settings.celery_task_default_queue,
        )
        task_id = celery_result.id

    summary = dict(run.raw_result_summary_json)
    summary["dispatch"] = build_dispatch_record(
        task_id=task_id,
        queue=settings.celery_task_default_queue,
        execution_mode=async_mode,
    )
    run.raw_result_summary_json = summary
    await session.commit()
    if settings.celery_task_always_eager:
        await execute_run(session, run.id)
    return DispatchResult(
        entity_type="run",
        entity_id=run.id,
        task_id=task_id,
        queued_at=queued_at,
        execution_mode=async_mode,
        queue=settings.celery_task_default_queue,
    )
