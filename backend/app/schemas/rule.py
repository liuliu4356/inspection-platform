from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RuleType, ScheduleType, SeverityLevel, TimeRangeType
from app.schemas.common import TimestampedReadModel


class RuleVersionPayload(BaseModel):
    query_config: dict[str, Any]
    threshold_config: dict[str, Any]
    expression_text: str | None = None
    change_note: str | None = None


class RuleBase(BaseModel):
    name: str = Field(max_length=128)
    code: str | None = Field(default=None, max_length=64)
    rule_type: RuleType
    datasource_id: UUID
    severity: SeverityLevel = SeverityLevel.warning
    enabled: bool = True
    schedule_type: ScheduleType = ScheduleType.manual
    cron_expr: str | None = Field(default=None, max_length=128)
    time_range_type: TimeRangeType = TimeRangeType.relative
    dimension_scope: dict[str, Any] = Field(default_factory=dict)


class RuleCreate(RuleBase, RuleVersionPayload):
    pass


class RuleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=128)
    code: str | None = Field(default=None, max_length=64)
    datasource_id: UUID | None = None
    severity: SeverityLevel | None = None
    enabled: bool | None = None
    schedule_type: ScheduleType | None = None
    cron_expr: str | None = Field(default=None, max_length=128)
    time_range_type: TimeRangeType | None = None
    dimension_scope: dict[str, Any] | None = None
    query_config: dict[str, Any] | None = None
    threshold_config: dict[str, Any] | None = None
    expression_text: str | None = None
    change_note: str | None = None


class RuleVersionRead(BaseModel):
    id: UUID
    version_no: int
    query_config_json: dict[str, Any]
    threshold_config_json: dict[str, Any]
    expression_text: str | None
    change_note: str | None


class RuleRead(TimestampedReadModel):
    name: str
    code: str | None
    rule_type: RuleType
    datasource_id: UUID
    severity: SeverityLevel
    enabled: bool
    schedule_type: ScheduleType
    cron_expr: str | None
    time_range_type: TimeRangeType
    dimension_scope_json: dict[str, Any]
    latest_version_no: int
    latest_version: RuleVersionRead | None = None


class RuleDryRunResult(BaseModel):
    rule_id: UUID
    valid: bool
    datasource_id: UUID
    rule_type: RuleType
    message: str
    normalized_query: dict[str, Any]
    threshold_preview: dict[str, Any]
    checked_at: datetime

