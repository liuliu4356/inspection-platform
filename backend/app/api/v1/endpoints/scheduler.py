from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import require_role
from app.db.session import get_db_session
from app.models.user import User
from app.services.scheduler_service import schedule_due_rules

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.post("/tick")
async def scheduler_tick(
    _: User = Depends(require_role(["admin", "operator"])),
) -> dict:
    async with get_db_session() as session:
        result = await schedule_due_rules(session)
    return {
        "checked_rules": result.checked_rules,
        "scheduled": result.scheduled,
        "skipped": result.skipped,
        "errors": result.errors,
    }
