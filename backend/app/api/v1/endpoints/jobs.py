from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.job import InspectionJob, InspectionTaskRun
from app.schemas.job import JobDetailRead, JobRead, ManualJobCreate, TaskRunRead
from app.services.job_service import cancel_job, create_manual_job, get_job_or_404

router = APIRouter(tags=["jobs"])


@router.post("/jobs/manual", response_model=JobDetailRead, status_code=status.HTTP_202_ACCEPTED)
async def trigger_manual_job(
    payload: ManualJobCreate,
    session: AsyncSession = Depends(get_db),
) -> JobDetailRead:
    job = await create_manual_job(session, payload)
    return JobDetailRead.model_validate(job)


@router.get("/jobs", response_model=list[JobRead])
async def list_jobs(session: AsyncSession = Depends(get_db)) -> list[JobRead]:
    result = await session.execute(select(InspectionJob).order_by(InspectionJob.created_at.desc()))
    jobs = result.scalars().all()
    return [JobRead.model_validate(job) for job in jobs]


@router.get("/jobs/{job_id}", response_model=JobDetailRead)
async def get_job(job_id: UUID, session: AsyncSession = Depends(get_db)) -> JobDetailRead:
    job = await get_job_or_404(session, job_id)
    return JobDetailRead.model_validate(job)


@router.get("/jobs/{job_id}/runs", response_model=list[TaskRunRead])
async def list_job_runs(job_id: UUID, session: AsyncSession = Depends(get_db)) -> list[TaskRunRead]:
    job = await get_job_or_404(session, job_id)
    return [TaskRunRead.model_validate(run) for run in job.runs]


@router.post("/jobs/{job_id}/cancel", response_model=JobDetailRead)
async def cancel_job_endpoint(job_id: UUID, session: AsyncSession = Depends(get_db)) -> JobDetailRead:
    job = await get_job_or_404(session, job_id)
    updated_job = await cancel_job(session, job)
    return JobDetailRead.model_validate(updated_job)


@router.get("/runs/{run_id}", response_model=TaskRunRead)
async def get_run(run_id: UUID, session: AsyncSession = Depends(get_db)) -> TaskRunRead:
    result = await session.execute(
        select(InspectionTaskRun).where(InspectionTaskRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task run not found")
    return TaskRunRead.model_validate(run)
