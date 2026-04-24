from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db, require_role
from app.models.datasource import Datasource
from app.models.enums import RuleType
from app.models.rule import InspectionRule, InspectionRuleVersion
from app.models.user import User
from app.schemas.rule import (
    RuleCreate,
    RuleDryRunResult,
    RuleRead,
    RuleUpdate,
    RuleVersionRead,
)

router = APIRouter(prefix="/rules", tags=["rules"])

_write_access = Depends(require_role(["admin", "operator"]))
_read_access = Depends(get_current_user)


async def _get_rule_or_404(session: AsyncSession, rule_id: UUID) -> InspectionRule:
    statement = (
        select(InspectionRule)
        .options(selectinload(InspectionRule.versions))
        .where(InspectionRule.id == rule_id)
    )
    result = await session.execute(statement)
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return rule


async def _ensure_datasource_exists(session: AsyncSession, datasource_id: UUID) -> None:
    datasource = await session.get(Datasource, datasource_id)
    if datasource is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Datasource not found")


def _latest_version(rule: InspectionRule) -> InspectionRuleVersion | None:
    if not rule.versions:
        return None
    return max(rule.versions, key=lambda item: item.version_no)


def _to_rule_read(rule: InspectionRule) -> RuleRead:
    latest_version = _latest_version(rule)
    version_payload = None
    if latest_version is not None:
        version_payload = RuleVersionRead(
            id=latest_version.id,
            version_no=latest_version.version_no,
            query_config_json=latest_version.query_config_json,
            threshold_config_json=latest_version.threshold_config_json,
            expression_text=latest_version.expression_text,
            change_note=latest_version.change_note,
        )
    return RuleRead(
        id=rule.id,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
        name=rule.name,
        code=rule.code,
        rule_type=rule.rule_type,
        datasource_id=rule.datasource_id,
        severity=rule.severity,
        enabled=rule.enabled,
        schedule_type=rule.schedule_type,
        cron_expr=rule.cron_expr,
        time_range_type=rule.time_range_type,
        dimension_scope_json=rule.dimension_scope_json,
        latest_version_no=rule.latest_version_no,
        latest_version=version_payload,
    )


def _validate_rule_config(rule_type: RuleType, query_config: dict[str, Any]) -> dict[str, Any]:
    if rule_type == RuleType.prometheus:
        query = query_config.get("query")
        if not isinstance(query, str) or not query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prometheus rule requires query_config.query",
            )
        return {"query": query.strip(), "step": query_config.get("step")}

    index = query_config.get("index") or query_config.get("indices")
    es_query = query_config.get("query")
    if not index or not isinstance(es_query, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Elasticsearch rule requires query_config.index and query_config.query",
        )
    return {"index": index, "query": es_query}


@router.get("", response_model=list[RuleRead])
async def list_rules(
    session: AsyncSession = Depends(get_db),
    _: User = _read_access,
) -> list[RuleRead]:
    statement = (
        select(InspectionRule)
        .options(selectinload(InspectionRule.versions))
        .order_by(InspectionRule.created_at.desc())
    )
    result = await session.execute(statement)
    rules = result.scalars().all()
    return [_to_rule_read(rule) for rule in rules]


@router.post("", response_model=RuleRead, status_code=status.HTTP_201_CREATED)
async def create_rule(
    payload: RuleCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = _write_access,
) -> RuleRead:
    await _ensure_datasource_exists(session, payload.datasource_id)
    _validate_rule_config(payload.rule_type, payload.query_config)

    rule = InspectionRule(
        name=payload.name,
        code=payload.code,
        rule_type=payload.rule_type,
        datasource_id=payload.datasource_id,
        severity=payload.severity,
        enabled=payload.enabled,
        schedule_type=payload.schedule_type,
        cron_expr=payload.cron_expr,
        time_range_type=payload.time_range_type,
        dimension_scope_json=payload.dimension_scope,
        latest_version_no=1,
        created_by=current_user.id,
    )
    session.add(rule)
    await session.flush()

    version = InspectionRuleVersion(
        rule_id=rule.id,
        version_no=1,
        query_config_json=payload.query_config,
        threshold_config_json=payload.threshold_config,
        expression_text=payload.expression_text,
        change_note=payload.change_note,
    )
    session.add(version)
    await session.commit()

    refreshed = await _get_rule_or_404(session, rule.id)
    return _to_rule_read(refreshed)


@router.get("/{rule_id}", response_model=RuleRead)
async def get_rule(
    rule_id: UUID,
    session: AsyncSession = Depends(get_db),
    _: User = _read_access,
) -> RuleRead:
    rule = await _get_rule_or_404(session, rule_id)
    return _to_rule_read(rule)


@router.get("/{rule_id}/versions", response_model=list[RuleVersionRead])
async def list_rule_versions(
    rule_id: UUID,
    session: AsyncSession = Depends(get_db),
    _: User = _read_access,
) -> list[RuleVersionRead]:
    await _get_rule_or_404(session, rule_id)
    result = await session.execute(
        select(InspectionRuleVersion)
        .where(InspectionRuleVersion.rule_id == rule_id)
        .order_by(InspectionRuleVersion.version_no.desc())
    )
    versions = result.scalars().all()
    return [
        RuleVersionRead(
            id=version.id,
            version_no=version.version_no,
            query_config_json=version.query_config_json,
            threshold_config_json=version.threshold_config_json,
            expression_text=version.expression_text,
            change_note=version.change_note,
        )
        for version in versions
    ]


@router.put("/{rule_id}", response_model=RuleRead)
async def update_rule(
    rule_id: UUID,
    payload: RuleUpdate,
    session: AsyncSession = Depends(get_db),
    _: User = _write_access,
) -> RuleRead:
    rule = await _get_rule_or_404(session, rule_id)
    updates = payload.model_dump(exclude_unset=True)

    if "datasource_id" in updates:
        await _ensure_datasource_exists(session, updates["datasource_id"])

    field_mapping = {
        "name": "name",
        "code": "code",
        "datasource_id": "datasource_id",
        "severity": "severity",
        "enabled": "enabled",
        "schedule_type": "schedule_type",
        "cron_expr": "cron_expr",
        "time_range_type": "time_range_type",
        "dimension_scope": "dimension_scope_json",
    }
    for source_field, target_field in field_mapping.items():
        if source_field in updates:
            setattr(rule, target_field, updates[source_field])

    latest_version = _latest_version(rule)
    should_create_version = any(
        key in updates for key in ("query_config", "threshold_config", "expression_text", "change_note")
    )

    if should_create_version:
        if latest_version is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Rule version history is missing",
            )
        next_version_no = rule.latest_version_no + 1
        query_config = updates.get("query_config", latest_version.query_config_json)
        threshold_config = updates.get("threshold_config", latest_version.threshold_config_json)
        expression_text = updates.get("expression_text", latest_version.expression_text)
        change_note = updates.get("change_note")
        _validate_rule_config(rule.rule_type, query_config)

        version = InspectionRuleVersion(
            rule_id=rule.id,
            version_no=next_version_no,
            query_config_json=query_config,
            threshold_config_json=threshold_config,
            expression_text=expression_text,
            change_note=change_note,
        )
        session.add(version)
        rule.latest_version_no = next_version_no

    await session.commit()
    refreshed = await _get_rule_or_404(session, rule.id)
    return _to_rule_read(refreshed)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: UUID,
    session: AsyncSession = Depends(get_db),
    _: User = _write_access,
) -> Response:
    rule = await _get_rule_or_404(session, rule_id)
    await session.delete(rule)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{rule_id}/dry-run", response_model=RuleDryRunResult)
async def dry_run_rule(
    rule_id: UUID,
    session: AsyncSession = Depends(get_db),
    _: User = _write_access,
) -> RuleDryRunResult:
    rule = await _get_rule_or_404(session, rule_id)
    latest_version = _latest_version(rule)
    if latest_version is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rule has no published version")

    normalized_query = _validate_rule_config(rule.rule_type, latest_version.query_config_json)
    return RuleDryRunResult(
        rule_id=rule.id,
        valid=True,
        datasource_id=rule.datasource_id,
        rule_type=rule.rule_type,
        message="Rule configuration passed structural validation",
        normalized_query=normalized_query,
        threshold_preview=latest_version.threshold_config_json,
        checked_at=datetime.now(UTC),
    )
