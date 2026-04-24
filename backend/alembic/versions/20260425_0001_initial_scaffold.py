"""initial scaffold

Revision ID: 20260425_0001
Revises:
Create Date: 2026-04-25 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260425_0001"
down_revision = None
branch_labels = None
depends_on = None


datasource_type = postgresql.ENUM("prometheus", "elasticsearch", name="datasource_type")
auth_type = postgresql.ENUM("none", "basic", "token", "api_key", name="auth_type")
rule_type = postgresql.ENUM("prometheus", "elasticsearch", name="rule_type")
severity_level = postgresql.ENUM("info", "warning", "critical", name="severity_level")
schedule_type = postgresql.ENUM("manual", "cron", name="schedule_type")
time_range_type = postgresql.ENUM("fixed", "relative", name="time_range_type")
job_status = postgresql.ENUM(
    "pending",
    "running",
    "success",
    "failed",
    "cancelled",
    "timeout",
    name="job_status",
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    bind = op.get_bind()
    datasource_type.create(bind, checkfirst=True)
    auth_type.create(bind, checkfirst=True)
    rule_type.create(bind, checkfirst=True)
    severity_level.create(bind, checkfirst=True)
    schedule_type.create(bind, checkfirst=True)
    time_range_type.create(bind, checkfirst=True)
    job_status.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255)),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=128), nullable=False),
    )

    op.create_table(
        "user_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_id"),
    )

    op.create_table(
        "datasources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("type", datasource_type, nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("auth_type", auth_type, nullable=False),
        sa.Column("auth_config_encrypted", sa.LargeBinary()),
        sa.Column("extra_config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("environment", sa.String(length=64)),
        sa.Column("idc", sa.String(length=64)),
        sa.Column("tags_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_check_status", sa.String(length=32)),
        sa.Column("last_check_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "inspection_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("code", sa.String(length=64), unique=True),
        sa.Column("rule_type", rule_type, nullable=False),
        sa.Column("datasource_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasources.id"), nullable=False),
        sa.Column("severity", severity_level, nullable=False, server_default="warning"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("schedule_type", schedule_type, nullable=False, server_default="manual"),
        sa.Column("cron_expr", sa.String(length=128)),
        sa.Column("time_range_type", time_range_type, nullable=False, server_default="relative"),
        sa.Column("dimension_scope_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("latest_version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "inspection_rule_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inspection_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("query_config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("threshold_config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expression_text", sa.Text()),
        sa.Column("change_note", sa.Text()),
        sa.UniqueConstraint("rule_id", "version_no", name="uq_rule_version"),
    )

    op.create_table(
        "inspection_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_no", sa.String(length=64), nullable=False, unique=True),
        sa.Column("trigger_type", sa.String(length=32), nullable=False),
        sa.Column("trigger_source", sa.String(length=32), nullable=False),
        sa.Column("status", job_status, nullable=False, server_default="pending"),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("range_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("range_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128)),
        sa.Column("summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "inspection_task_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inspection_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inspection_rules.id"), nullable=False),
        sa.Column("datasource_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasources.id"), nullable=False),
        sa.Column("status", job_status, nullable=False, server_default="pending"),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("worker_name", sa.String(length=128)),
        sa.Column("query_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("raw_result_summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("score", sa.Numeric(10, 2)),
        sa.Column("severity", severity_level),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "inspection_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inspection_task_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("finding_type", sa.String(length=64), nullable=False),
        sa.Column("finding_key", sa.String(length=128)),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text()),
        sa.Column("severity", severity_level, nullable=False),
        sa.Column("metric_name", sa.String(length=255)),
        sa.Column("labels_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("evidence_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("suggestion", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "inspection_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inspection_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("report_no", sa.String(length=64), nullable=False, unique=True),
        sa.Column("format", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("overview_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("storage_path", sa.Text()),
        sa.Column("generated_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=36)),
        sa.Column("detail_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("idx_datasources_type_enabled", "datasources", ["type", "enabled"])
    op.create_index("idx_rules_datasource_enabled", "inspection_rules", ["datasource_id", "enabled"])
    op.create_index("idx_jobs_status_created_at", "inspection_jobs", ["status", "created_at"])
    op.create_index("idx_runs_job_status", "inspection_task_runs", ["job_id", "status"])
    op.create_index("idx_findings_run_severity", "inspection_findings", ["run_id", "severity"])
    op.create_index("idx_audit_logs_resource", "audit_logs", ["resource_type", "resource_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_audit_logs_resource", table_name="audit_logs")
    op.drop_index("idx_findings_run_severity", table_name="inspection_findings")
    op.drop_index("idx_runs_job_status", table_name="inspection_task_runs")
    op.drop_index("idx_jobs_status_created_at", table_name="inspection_jobs")
    op.drop_index("idx_rules_datasource_enabled", table_name="inspection_rules")
    op.drop_index("idx_datasources_type_enabled", table_name="datasources")

    op.drop_table("audit_logs")
    op.drop_table("inspection_reports")
    op.drop_table("inspection_findings")
    op.drop_table("inspection_task_runs")
    op.drop_table("inspection_jobs")
    op.drop_table("inspection_rule_versions")
    op.drop_table("inspection_rules")
    op.drop_table("datasources")
    op.drop_table("user_roles")
    op.drop_table("roles")
    op.drop_table("users")

    bind = op.get_bind()
    job_status.drop(bind, checkfirst=True)
    time_range_type.drop(bind, checkfirst=True)
    schedule_type.drop(bind, checkfirst=True)
    severity_level.drop(bind, checkfirst=True)
    rule_type.drop(bind, checkfirst=True)
    auth_type.drop(bind, checkfirst=True)
    datasource_type.drop(bind, checkfirst=True)

