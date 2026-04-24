from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import JobStatus
from app.models.job import InspectionJob, InspectionTaskRun
from app.models.rule import InspectionRule, InspectionRuleVersion
from app.schemas.job import ManualJobCreate


def _latest_version(rule: InspectionRule) -> InspectionRuleVersion | None:
    if not rule.versions:
        return None
    return max(rule.versions, key=lambda item: item.version_no)


def _generate_job_no() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    suffix = uuid4().hex[:8].upper()
    return f"JOB-{timestamp}-{suffix}"


async def create_manual_job(session: AsyncSession, payload: ManualJobCreate) -> InspectionJob:
    if payload.idempotency_key:
        existing_result = await session.execute(
            select(InspectionJob)
            .options(selectinload(InspectionJob.runs))
            .where(InspectionJob.idempotency_key == payload.idempotency_key)
        )
        existing_job = existing_result.scalar_one_or_none()
        if existing_job is not None:
            return existing_job

    statement = (
        select(InspectionRule)
        .options(selectinload(InspectionRule.versions))
        .where(InspectionRule.id.in_(payload.rule_ids))
    )
    result = await session.execute(statement)
    rules = result.scalars().all()
    found_rule_ids = {rule.id for rule in rules}
    missing_rule_ids = [rule_id for rule_id in payload.rule_ids if rule_id not in found_rule_ids]
    if missing_rule_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rules not found: {', '.join(str(rule_id) for rule_id in missing_rule_ids)}",
        )

    disabled_rules = [rule.id for rule in rules if not rule.enabled]
    if disabled_rules:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rules are disabled: {', '.join(str(rule_id) for rule_id in disabled_rules)}",
        )

    job = InspectionJob(
        job_no=_generate_job_no(),
        trigger_type="manual",
        trigger_source=payload.trigger_source,
        status=JobStatus.pending,
        range_start=payload.range_start,
        range_end=payload.range_end,
        idempotency_key=payload.idempotency_key,
        summary_json={
            "requested_rule_count": len(rules),
            "pending_run_count": len(rules),
        },
    )
    session.add(job)
    await session.flush()

    for rule in rules:
        latest_version = _latest_version(rule)
        if latest_version is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Rule has no published version: {rule.id}",
            )
        session.add(
            InspectionTaskRun(
                job_id=job.id,
                rule_id=rule.id,
                datasource_id=rule.datasource_id,
                status=JobStatus.pending,
                attempt=1,
                query_snapshot_json={
                    "rule_version_no": latest_version.version_no,
                    "query_config": latest_version.query_config_json,
                    "threshold_config": latest_version.threshold_config_json,
                    "dimension_scope": rule.dimension_scope_json,
                    "range_start": payload.range_start.isoformat(),
                    "range_end": payload.range_end.isoformat(),
                },
                raw_result_summary_json={},
            )
        )

    await session.commit()
    refreshed_result = await session.execute(
        select(InspectionJob)
        .options(selectinload(InspectionJob.runs))
        .where(InspectionJob.id == job.id)
    )
    return refreshed_result.scalar_one()


async def get_job_or_404(session: AsyncSession, job_id: UUID) -> InspectionJob:
    result = await session.execute(
        select(InspectionJob)
        .options(selectinload(InspectionJob.runs))
        .where(InspectionJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


async def cancel_job(session: AsyncSession, job: InspectionJob) -> InspectionJob:
    if job.status in {JobStatus.success, JobStatus.failed, JobStatus.cancelled, JobStatus.timeout}:
        return job

    job.status = JobStatus.cancelled
    job.finished_at = datetime.now(UTC)

    for run in job.runs:
        if run.status in {JobStatus.pending, JobStatus.running}:
            run.status = JobStatus.cancelled
            run.finished_at = job.finished_at

    summary = dict(job.summary_json)
    summary["pending_run_count"] = sum(1 for run in job.runs if run.status == JobStatus.pending)
    summary["cancelled_run_count"] = sum(1 for run in job.runs if run.status == JobStatus.cancelled)
    job.summary_json = summary

    await session.commit()
    return await get_job_or_404(session, job.id)

