from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.crypto import decrypt_json
from app.models.enums import JobStatus, SeverityLevel
from app.models.job import InspectionFinding, InspectionJob, InspectionTaskRun
from app.models.rule import InspectionRule, InspectionRuleVersion
from app.schemas.job import ManualJobCreate
from app.services.inspection_executor import evaluate_threshold, execute_query_snapshot

settings = get_settings()


def _latest_version(rule: InspectionRule) -> InspectionRuleVersion | None:
    if not rule.versions:
        return None
    return max(rule.versions, key=lambda item: item.version_no)


def _generate_job_no() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    suffix = uuid4().hex[:8].upper()
    return f"JOB-{timestamp}-{suffix}"


def _generate_finding_key() -> str:
    return uuid4().hex[:12]


def _normalize_job_summary(runs: list[InspectionTaskRun], current_summary: dict[str, Any]) -> dict[str, Any]:
    summary = dict(current_summary)
    summary.update(
        {
            "requested_rule_count": len(runs),
            "pending_run_count": sum(1 for run in runs if run.status == JobStatus.pending),
            "running_run_count": sum(1 for run in runs if run.status == JobStatus.running),
            "success_run_count": sum(1 for run in runs if run.status == JobStatus.success),
            "failed_run_count": sum(1 for run in runs if run.status == JobStatus.failed),
            "cancelled_run_count": sum(1 for run in runs if run.status == JobStatus.cancelled),
            "timeout_run_count": sum(1 for run in runs if run.status == JobStatus.timeout),
            "warning_finding_count": sum(1 for run in runs if run.severity == SeverityLevel.warning),
            "critical_finding_count": sum(1 for run in runs if run.severity == SeverityLevel.critical),
        }
    )
    return summary


def _derive_job_status(runs: list[InspectionTaskRun]) -> JobStatus:
    statuses = {run.status for run in runs}
    if JobStatus.running in statuses:
        return JobStatus.running
    if JobStatus.pending in statuses:
        return JobStatus.pending
    if JobStatus.failed in statuses:
        return JobStatus.failed
    if statuses == {JobStatus.cancelled}:
        return JobStatus.cancelled
    if JobStatus.timeout in statuses:
        return JobStatus.timeout
    return JobStatus.success


async def _recalculate_job(session: AsyncSession, job_id: UUID) -> InspectionJob:
    job = await get_job_or_404(session, job_id)
    job.summary_json = _normalize_job_summary(job.runs, job.summary_json)
    job.status = _derive_job_status(job.runs)

    started_candidates = [run.started_at for run in job.runs if run.started_at is not None]
    finished_candidates = [run.finished_at for run in job.runs if run.finished_at is not None]
    if started_candidates:
        job.started_at = min(started_candidates)
    if job.status not in {JobStatus.pending, JobStatus.running} and finished_candidates:
        job.finished_at = max(finished_candidates)
    else:
        job.finished_at = None

    await session.commit()
    return await get_job_or_404(session, job_id)


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
        .options(
            selectinload(InspectionJob.runs).selectinload(InspectionTaskRun.findings),
        )
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


async def get_run_or_404(session: AsyncSession, run_id: UUID) -> InspectionTaskRun:
    result = await session.execute(
        select(InspectionTaskRun)
        .options(
            selectinload(InspectionTaskRun.datasource),
            selectinload(InspectionTaskRun.rule).selectinload(InspectionRule.versions),
            selectinload(InspectionTaskRun.job),
            selectinload(InspectionTaskRun.findings),
        )
        .where(InspectionTaskRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task run not found")
    return run


async def _build_error_finding(
    *,
    run: InspectionTaskRun,
    title: str,
    message: str,
    evidence: dict[str, Any],
) -> InspectionFinding:
    return InspectionFinding(
        run_id=run.id,
        finding_type="execution_error",
        finding_key=_generate_finding_key(),
        title=title,
        message=message,
        severity=run.rule.severity,
        metric_name=run.rule.code or run.rule.name,
        labels_json=run.rule.dimension_scope_json,
        evidence_json=evidence,
        suggestion="Check datasource connectivity, query syntax, and threshold configuration.",
    )


async def execute_run(session: AsyncSession, run_id: UUID) -> InspectionTaskRun:
    run = await get_run_or_404(session, run_id)
    if run.status == JobStatus.running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task run is already executing",
        )
    if run.status == JobStatus.cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cancelled task runs cannot be executed",
        )

    now = datetime.now(UTC)
    if run.status in {JobStatus.failed, JobStatus.timeout, JobStatus.success} or run.started_at is not None:
        run.attempt += 1

    run.findings.clear()
    run.status = JobStatus.running
    run.started_at = now
    run.finished_at = None
    run.error_message = None
    run.raw_result_summary_json = {}
    run.score = None
    run.severity = None
    await session.flush()

    threshold_config = run.query_snapshot_json.get("threshold_config", {})

    try:
        query_result = await execute_query_snapshot(
            datasource=run.datasource,
            query_snapshot=run.query_snapshot_json,
            auth_config=decrypt_json(run.datasource.auth_config_encrypted),
            timeout_seconds=settings.http_timeout_seconds,
        )
        evaluation = evaluate_threshold(
            rule=run.rule,
            observed_value=query_result.observed_value,
            threshold_config=threshold_config,
        )
        run.score = evaluation.observed_value
        run.severity = evaluation.severity
        run.status = JobStatus.success
        run.finished_at = datetime.now(UTC)
        run.raw_result_summary_json = {
            **query_result.summary,
            "observed_value": evaluation.observed_value,
            "evaluation_message": evaluation.message,
            "threshold_snapshot": evaluation.threshold_snapshot,
        }

        if evaluation.finding_required:
            run.findings.append(
                InspectionFinding(
                    run_id=run.id,
                    finding_type="threshold_breach",
                    finding_key=_generate_finding_key(),
                    title=f"{run.rule.name} threshold breached",
                    message=evaluation.message,
                    severity=evaluation.severity,
                    metric_name=query_result.metric_name or run.rule.code or run.rule.name,
                    labels_json=query_result.labels or run.rule.dimension_scope_json,
                    evidence_json=run.raw_result_summary_json,
                    suggestion=threshold_config.get(
                        "suggestion",
                        "Review the datasource output and adjust thresholds or workloads as needed.",
                    ),
                )
            )
    except Exception as exc:
        run.status = JobStatus.failed
        run.finished_at = datetime.now(UTC)
        run.error_message = str(exc)
        run.severity = run.rule.severity
        run.raw_result_summary_json = {
            "error": str(exc),
            "query_snapshot": run.query_snapshot_json,
        }
        run.findings.append(
            await _build_error_finding(
                run=run,
                title=f"{run.rule.name} execution failed",
                message=str(exc),
                evidence=run.raw_result_summary_json,
            )
        )

    await session.commit()
    await _recalculate_job(session, run.job_id)
    return await get_run_or_404(session, run.id)


async def execute_job(session: AsyncSession, job_id: UUID) -> InspectionJob:
    job = await get_job_or_404(session, job_id)
    executable_runs = [
        run.id
        for run in job.runs
        if run.status in {JobStatus.pending, JobStatus.failed, JobStatus.timeout}
    ]
    if not executable_runs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending or retryable runs found for this job",
        )

    job.status = JobStatus.running
    job.started_at = job.started_at or datetime.now(UTC)
    await session.commit()

    for run_id in executable_runs:
        await execute_run(session, run_id)

    return await get_job_or_404(session, job_id)
