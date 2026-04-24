from __future__ import annotations

import asyncio
from uuid import UUID

from app.core.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.services.job_service import execute_job, execute_run


async def _execute_job(job_id: str) -> dict[str, str]:
    async with AsyncSessionLocal() as session:
        job = await execute_job(session, UUID(job_id))
        return {"job_id": str(job.id), "status": job.status.value}


async def _execute_run(run_id: str) -> dict[str, str]:
    async with AsyncSessionLocal() as session:
        run = await execute_run(session, UUID(run_id))
        return {"run_id": str(run.id), "status": run.status.value}


@celery_app.task(name="inspection.execute_job")
def execute_job_task(job_id: str) -> dict[str, str]:
    return asyncio.run(_execute_job(job_id))


@celery_app.task(name="inspection.execute_run")
def execute_run_task(run_id: str) -> dict[str, str]:
    return asyncio.run(_execute_run(run_id))

