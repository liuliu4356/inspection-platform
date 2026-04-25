"""ELK 巡检 API 端点"""
from __future__ import annotations

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_role
from app.models.user import User
from app.models.enums import DatasourceType
from app.schemas.common import PaginatedResponse
from app.schemas.datasource import DatasourceCreate, DatasourceRead, DatasourceUpdate
from app.services.elk_inspector import ELKInspectionExecutor, ELKClient

router = APIRouter(prefix="/elk", tags=["elk"])


def get_default_config() -> str:
    return "config/elk_inspection.yaml"


@router.get("/inspection/config")
async def get_elk_config(
    _: User = Depends(get_current_user),
) -> dict:
    """获取 ELK 巡检配置"""
    executor = ELKInspectionExecutor(get_default_config())
    return executor.config


@router.get("/inspection/run")
async def run_elk_inspection(
    datasource: str = Query(None, description="Elasticsearch 地址"),
    username: str = Query("", description="用户名"),
    password: str = Query("", description="密码"),
    _: User = Depends(get_current_user),
) -> dict:
    """手动触发 ELK 巡检"""
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请提供 Elasticsearch 地址",
        )

    executor = ELKInspectionExecutor()
    result = await executor.inspect(datasource, username, password)
    return result.to_dict()


@router.get("/inspection/run/{datasource_id}")
async def run_elk_inspection_by_id(
    datasource_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["admin", "operator"])),
) -> dict:
    """通过数据源 ID 触发 ELK 巡检"""
    from app.models.datasource import Datasource

    datasource = await session.get(Datasource, datasource_id)
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数据源不存在",
        )

    if datasource.type != DatasourceType.elk:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="数据源类型不是 ELK",
        )

    from app.core.crypto import decrypt_json

    auth_config = decrypt_json(datasource.auth_config_encrypted) if datasource.auth_config_encrypted else {}

    executor = ELKInspectionExecutor()
    result = await executor.inspect(
        datasource.endpoint,
        auth_config.get("username", ""),
        auth_config.get("password", ""),
    )
    return result.to_dict()


@router.get("/cluster/{cluster_name}/health")
async def get_cluster_health(
    cluster_name: str,
    datasource: str = Query(..., description="Elasticsearch 地址"),
    username: str = Query("", description="用户名"),
    password: str = Query("", description="密码"),
    _: User = Depends(get_current_user),
) -> dict:
    """获取集群健康状态"""
    client = ELKClient(datasource, username, password)
    return await client.cluster_health()


@router.get("/cluster/{cluster_name}/stats")
async def get_cluster_stats(
    cluster_name: str,
    datasource: str = Query(..., description="Elasticsearch 地址"),
    username: str = Query("", description="用户名"),
    password: str = Query("", description="密码"),
    _: User = Depends(get_current_user),
) -> dict:
    """获取集群统计信息"""
    client = ELKClient(datasource, username, password)
    return await client.cluster_stats()


@router.get("/nodes/stats")
async def get_nodes_stats(
    datasource: str = Query(..., description="Elasticsearch 地址"),
    username: str = Query("", description="用户名"),
    password: str = Query("", description="密码"),
    _: User = Depends(get_current_user),
) -> dict:
    """获取节点统计"""
    client = ELKClient(datasource, username, password)
    return await client.nodes_stats()


@router.get("/indices/stats")
async def get_indices_stats(
    datasource: str = Query(..., description="Elasticsearch 地址"),
    index: str = Query("*", description="索引名称"),
    username: str = Query("", description="用户名"),
    password: str = Query("", description="密码"),
    _: User = Depends(get_current_user),
) -> dict:
    """获取索引统计"""
    client = ELKClient(datasource, username, password)
    return await client.indices_stats(index)


@router.post("/datasources")
async def create_elk_datasource(
    payload: DatasourceCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "operator"])),
) -> DatasourceRead:
    """创建 ELK 数据源"""
    if payload.type != DatasourceType.elk:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请选择 ELK 数据源类型",
        )

    from app.models.datasource import Datasource
    from app.core.crypto import encrypt_json

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


@router.get("/report/{inspection_id}")
async def get_elk_report(
    inspection_id: uuid.UUID,
    _: User = Depends(get_current_user),
) -> HTMLResponse:
    """获取 ELK 巡检报告"""
    from app.services.report_generator import generate_html_report

    try:
        html = await generate_html_report(inspection_id)
        return HTMLResponse(content=html)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))