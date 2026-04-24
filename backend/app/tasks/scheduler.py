from __future__ import annotations

import asyncio

from app.core.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.services.scheduler_service import schedule_due_rules


async def _run_scheduler_tick() -> dict:
    async with AsyncSessionLocal() as session:
        result = await schedule_due_rules(session)
        return {
            "checked_rules": result.checked_rules,
            "scheduled": result.scheduled,
            "skipped": result.skipped,
            "errors": result.errors,
        }


@celery_app.task(name="inspection.scheduler_tick")
def scheduler_tick() -> dict:
    return asyncio.run(_run_scheduler_tick())
