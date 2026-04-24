from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AuthType, DatasourceType
from app.schemas.common import TimestampedReadModel


class DatasourceBase(BaseModel):
    name: str = Field(max_length=128)
    type: DatasourceType
    endpoint: str
    auth_type: AuthType
    environment: str | None = None
    idc: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)
    extra_config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class DatasourceCreate(DatasourceBase):
    auth_config: dict[str, Any] = Field(default_factory=dict)


class DatasourceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=128)
    endpoint: str | None = None
    auth_type: AuthType | None = None
    auth_config: dict[str, Any] | None = None
    environment: str | None = None
    idc: str | None = None
    tags: dict[str, str] | None = None
    extra_config: dict[str, Any] | None = None
    enabled: bool | None = None


class DatasourceRead(TimestampedReadModel):
    name: str
    type: DatasourceType
    endpoint: str
    auth_type: AuthType
    environment: str | None
    idc: str | None
    tags_json: dict[str, Any]
    extra_config_json: dict[str, Any]
    enabled: bool
    last_check_status: str | None
    last_check_at: datetime | None


class DatasourceTestResult(BaseModel):
    datasource_id: UUID
    success: bool
    message: str
    checked_at: datetime
    details: dict[str, Any] = Field(default_factory=dict)

