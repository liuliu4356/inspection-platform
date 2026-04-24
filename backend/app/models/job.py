from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import JobStatus, SeverityLevel

if TYPE_CHECKING:
    from app.models.datasource import Datasource
    from app.models.report import InspectionReport
    from app.models.rule import InspectionRule


class InspectionJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "inspection_jobs"

    job_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_source: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"),
        default=JobStatus.pending,
        nullable=False,
    )
    requested_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    range_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    range_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128))
    summary_json: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    runs: Mapped[list["InspectionTaskRun"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )
    reports: Mapped[list["InspectionReport"]] = relationship(back_populates="job")


class InspectionTaskRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "inspection_task_runs"

    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("inspection_jobs.id", ondelete="CASCADE"))
    rule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("inspection_rules.id"), nullable=False)
    datasource_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasources.id"), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"),
        default=JobStatus.pending,
        nullable=False,
    )
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    worker_name: Mapped[str | None] = mapped_column(String(128))
    query_snapshot_json: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )
    raw_result_summary_json: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )
    score: Mapped[float | None] = mapped_column(Numeric(10, 2))
    severity: Mapped[SeverityLevel | None] = mapped_column(Enum(SeverityLevel, name="severity_level"))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    job: Mapped["InspectionJob"] = relationship(back_populates="runs")
    datasource: Mapped["Datasource"] = relationship(back_populates="task_runs")
    rule: Mapped["InspectionRule"] = relationship(back_populates="task_runs")
    findings: Mapped[list["InspectionFinding"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class InspectionFinding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "inspection_findings"

    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("inspection_task_runs.id", ondelete="CASCADE"))
    finding_type: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_key: Mapped[str | None] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[SeverityLevel] = mapped_column(Enum(SeverityLevel, name="severity_level"))
    metric_name: Mapped[str | None] = mapped_column(String(255))
    labels_json: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )
    evidence_json: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )
    suggestion: Mapped[str | None] = mapped_column(Text)

    run: Mapped["InspectionTaskRun"] = relationship(back_populates="findings")
