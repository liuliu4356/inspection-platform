from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_role
from app.core.config import get_settings
from app.core.crypto import decrypt_json, encrypt_json
from app.models.datasource import Datasource
from app.models.user import User
from app.schemas.datasource import (
    DatasourceCreate,
    DatasourceRead,
    DatasourceTestResult,
    DatasourceUpdate,
)
from app.services.datasource_probe import probe_datasource

router = APIRouter(prefix="/datasources", tags=["datasources"])
settings = get_settings()

_write_access = Depends(require_role(["admin", "operator"]))
_read_access = Depends(get_current_user)


async def _get_datasource_or_404(session: AsyncSession, datasource_id: UUID) -> Datasource:
    datasource = await session.get(Datasource, datasource_id)
    if datasource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Datasource not found")
    return datasource


@router.get("", response_model=list[DatasourceRead])
async def list_datasources(
    session: AsyncSession = Depends(get_db),
    _: User = _read_access,
) -> list[DatasourceRead]:
    result = await session.execute(select(Datasource).order_by(Datasource.created_at.desc()))
    datasources = result.scalars().all()
    return [DatasourceRead.model_validate(item) for item in datasources]


@router.post("", response_model=DatasourceRead, status_code=status.HTTP_201_CREATED)
async def create_datasource(
    payload: DatasourceCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = _write_access,
) -> DatasourceRead:
    datasource = Datasource(
        name=payload.name,
        type=payload.type,
        endpoint=payload.endpoint,
        auth_type=payload.auth_type,
        auth_config_encrypted=encrypt_json(payload.auth_config),
        extra_config_json=payload.extra_config,
        environment=payload.environment,
        idc=payload.idc,
        tags_json=payload.tags,
        enabled=payload.enabled,
        created_by=current_user.id,
    )
    session.add(datasource)
    await session.commit()
    await session.refresh(datasource)
    return DatasourceRead.model_validate(datasource)


@router.get("/{datasource_id}", response_model=DatasourceRead)
async def get_datasource(
    datasource_id: UUID,
    session: AsyncSession = Depends(get_db),
    _: User = _read_access,
) -> DatasourceRead:
    datasource = await _get_datasource_or_404(session, datasource_id)
    return DatasourceRead.model_validate(datasource)


@router.put("/{datasource_id}", response_model=DatasourceRead)
async def update_datasource(
    datasource_id: UUID,
    payload: DatasourceUpdate,
    session: AsyncSession = Depends(get_db),
    _: User = _write_access,
) -> DatasourceRead:
    datasource = await _get_datasource_or_404(session, datasource_id)
    updates = payload.model_dump(exclude_unset=True)

    field_mapping = {
        "name": "name",
        "endpoint": "endpoint",
        "auth_type": "auth_type",
        "environment": "environment",
        "idc": "idc",
        "enabled": "enabled",
        "tags": "tags_json",
        "extra_config": "extra_config_json",
    }
    for source_field, target_field in field_mapping.items():
        if source_field in updates:
            setattr(datasource, target_field, updates[source_field])

    if "auth_config" in updates:
        datasource.auth_config_encrypted = encrypt_json(updates["auth_config"])

    await session.commit()
    await session.refresh(datasource)
    return DatasourceRead.model_validate(datasource)


@router.delete("/{datasource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_datasource(
    datasource_id: UUID,
    session: AsyncSession = Depends(get_db),
    _: User = _write_access,
) -> Response:
    datasource = await _get_datasource_or_404(session, datasource_id)
    await session.delete(datasource)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{datasource_id}/test", response_model=DatasourceTestResult)
async def test_datasource(
    datasource_id: UUID,
    session: AsyncSession = Depends(get_db),
    _: User = _write_access,
) -> DatasourceTestResult:
    datasource = await _get_datasource_or_404(session, datasource_id)
    checked_at = datetime.now(UTC)

    try:
        probe_result = await probe_datasource(
            datasource_type=datasource.type,
            endpoint=datasource.endpoint,
            auth_type=datasource.auth_type,
            auth_config=decrypt_json(datasource.auth_config_encrypted),
            extra_config=datasource.extra_config_json,
            timeout_seconds=settings.http_timeout_seconds,
        )
    except Exception as exc:
        datasource.last_check_status = "failed"
        datasource.last_check_at = checked_at
        await session.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    datasource.last_check_status = "success" if probe_result.success else "failed"
    datasource.last_check_at = checked_at
    await session.commit()

    return DatasourceTestResult(
        datasource_id=datasource.id,
        success=probe_result.success,
        message=probe_result.message,
        checked_at=checked_at,
        details=probe_result.details,
    )
