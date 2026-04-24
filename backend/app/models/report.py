from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.job import InspectionJob


class InspectionReport(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "inspection_reports"

    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("inspection_jobs.id", ondelete="CASCADE"))
    report_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    overview_json: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )
    storage_path: Mapped[str | None] = mapped_column(Text)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    job: Mapped["InspectionJob"] = relationship(back_populates="reports")
