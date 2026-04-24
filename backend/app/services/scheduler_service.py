from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from croniter import croniter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import JobStatus
from app.models.job import InspectionJob, InspectionTaskRun
from app.models.rule import InspectionRule
from app.services.job_service import _latest_version


@dataclass
class SchedulerResult:
    checked_rules: int = 0
    scheduled: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def _generate_job_no() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    suffix = uuid4().hex[:8].upper()
    return f"SCHED-{timestamp}-{suffix}"


async def schedule_due_rules(session: AsyncSession, now: datetime | None = None) -> SchedulerResult:
    """Check all enabled cron rules and create jobs for due schedules.

    Accepts an optional *now* parameter for deterministic testing.
    """
    result = SchedulerResult()

    statement = (
        select(InspectionRule)
        .options(selectinload(InspectionRule.versions))
        .where(
            InspectionRule.enabled.is_(True),
            InspectionRule.schedule_type == "cron",
            InspectionRule.cron_expr.isnot(None),
        )
    )
    rows = await session.execute(statement)
    rules = rows.scalars().all()
    result.checked_rules = len(rules)

    now = now or datetime.now(UTC)

    for rule in rules:
        if not rule.cron_expr:
            continue

        try:
            cron = croniter(rule.cron_expr, now)
            prev_fire = cron.get_prev(datetime)
        except (ValueError, KeyError) as exc:
            result.errors.append(f"Rule {rule.id}: invalid cron expression '{rule.cron_expr}': {exc}")
            continue

        period_key = prev_fire.strftime("%Y%m%d%H%M")
        idempotency_key = f"scheduled:{rule.id}:{period_key}"

        existing = await session.execute(
            select(InspectionJob).where(InspectionJob.idempotency_key == idempotency_key)
        )
        if existing.scalar_one_or_none() is not None:
            result.skipped += 1
            continue

        latest_ver = _latest_version(rule)
        if latest_ver is None:
            result.errors.append(f"Rule {rule.id}: no published version")
            continue

        job = InspectionJob(
            job_no=_generate_job_no(),
            trigger_type="scheduled",
            trigger_source="scheduler",
            status=JobStatus.pending,
            range_start=prev_fire,
            range_end=now,
            idempotency_key=idempotency_key,
            summary_json={"scheduled_rule": str(rule.id), "cron_expr": rule.cron_expr},
        )
        session.add(job)
        await session.flush()

        session.add(
            InspectionTaskRun(
                job_id=job.id,
                rule_id=rule.id,
                datasource_id=rule.datasource_id,
                status=JobStatus.pending,
                attempt=1,
                query_snapshot_json={
                    "rule_version_no": latest_ver.version_no,
                    "query_config": latest_ver.query_config_json,
                    "threshold_config": latest_ver.threshold_config_json,
                    "dimension_scope": rule.dimension_scope_json,
                    "range_start": prev_fire.isoformat(),
                    "range_end": now.isoformat(),
                },
                raw_result_summary_json={},
            )
        )
        result.scheduled += 1

    await session.commit()
    return result
