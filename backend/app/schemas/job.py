from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import JobStatus, SeverityLevel
from app.schemas.common import ORMBaseModel, TimestampedReadModel


class ManualJobCreate(BaseModel):
    rule_ids: list[UUID] = Field(min_length=1)
    range_start: datetime
    range_end: datetime
    trigger_source: str = Field(default="ui", max_length=32)
    idempotency_key: str | None = Field(default=None, max_length=128)

    @field_validator("rule_ids")
    @classmethod
    def deduplicate_rule_ids(cls, value: list[UUID]) -> list[UUID]:
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def validate_range(self) -> "ManualJobCreate":
        if self.range_end <= self.range_start:
            raise ValueError("range_end must be greater than range_start")
        return self


class TaskRunRead(ORMBaseModel):
    id: UUID
    job_id: UUID
    rule_id: UUID
    datasource_id: UUID
    status: JobStatus
    attempt: int
    worker_name: str | None
    query_snapshot_json: dict[str, Any]
    raw_result_summary_json: dict[str, Any]
    score: float | None
    severity: SeverityLevel | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None


class JobRead(TimestampedReadModel):
    job_no: str
    trigger_type: str
    trigger_source: str
    status: JobStatus
    requested_by: UUID | None
    range_start: datetime
    range_end: datetime
    idempotency_key: str | None
    summary_json: dict[str, Any]
    started_at: datetime | None
    finished_at: datetime | None


class JobDetailRead(JobRead):
    runs: list[TaskRunRead] = Field(default_factory=list)

