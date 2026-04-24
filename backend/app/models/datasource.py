from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, LargeBinary, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AuthType, DatasourceType

if TYPE_CHECKING:
    from app.models.job import InspectionTaskRun
    from app.models.rule import InspectionRule


class Datasource(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "datasources"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    type: Mapped[DatasourceType] = mapped_column(Enum(DatasourceType, name="datasource_type"))
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    auth_type: Mapped[AuthType] = mapped_column(Enum(AuthType, name="auth_type"))
    auth_config_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    extra_config_json: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )
    environment: Mapped[str | None] = mapped_column(String(64))
    idc: Mapped[str | None] = mapped_column(String(64))
    tags_json: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_check_status: Mapped[str | None] = mapped_column(String(32))
    last_check_at: Mapped[datetime | None]
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    rules: Mapped[list["InspectionRule"]] = relationship(back_populates="datasource")
    task_runs: Mapped[list["InspectionTaskRun"]] = relationship(back_populates="datasource")
