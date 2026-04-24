from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import RuleType, ScheduleType, SeverityLevel, TimeRangeType

if TYPE_CHECKING:
    from app.models.datasource import Datasource
    from app.models.job import InspectionTaskRun


class InspectionRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "inspection_rules"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    code: Mapped[str | None] = mapped_column(String(64), unique=True)
    rule_type: Mapped[RuleType] = mapped_column(Enum(RuleType, name="rule_type"))
    datasource_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasources.id"), nullable=False)
    severity: Mapped[SeverityLevel] = mapped_column(
        Enum(SeverityLevel, name="severity_level"),
        default=SeverityLevel.warning,
        nullable=False,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    schedule_type: Mapped[ScheduleType] = mapped_column(
        Enum(ScheduleType, name="schedule_type"),
        default=ScheduleType.manual,
        nullable=False,
    )
    cron_expr: Mapped[str | None] = mapped_column(String(128))
    time_range_type: Mapped[TimeRangeType] = mapped_column(
        Enum(TimeRangeType, name="time_range_type"),
        default=TimeRangeType.relative,
        nullable=False,
    )
    dimension_scope_json: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )
    latest_version_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    datasource: Mapped["Datasource"] = relationship(back_populates="rules")
    versions: Mapped[list["InspectionRuleVersion"]] = relationship(
        back_populates="rule",
        cascade="all, delete-orphan",
        order_by="InspectionRuleVersion.version_no",
    )
    task_runs: Mapped[list["InspectionTaskRun"]] = relationship(back_populates="rule")


class InspectionRuleVersion(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "inspection_rule_versions"
    __table_args__ = (UniqueConstraint("rule_id", "version_no"),)

    rule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("inspection_rules.id", ondelete="CASCADE"))
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    query_config_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    threshold_config_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    expression_text: Mapped[str | None] = mapped_column(Text)
    change_note: Mapped[str | None] = mapped_column(Text)

    rule: Mapped["InspectionRule"] = relationship(back_populates="versions")
