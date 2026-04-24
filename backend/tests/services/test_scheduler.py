from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from croniter import croniter

from app.services.scheduler_service import SchedulerResult, schedule_due_rules


class TestCroniterParsing:
    def test_croniter_every_5_minutes(self) -> None:
        base = datetime(2026, 4, 25, 10, 3, 0, tzinfo=UTC)
        cron = croniter("*/5 * * * *", base)
        prev = cron.get_prev(datetime)
        assert prev == datetime(2026, 4, 25, 10, 0, 0, tzinfo=UTC)

    def test_croniter_hourly(self) -> None:
        base = datetime(2026, 4, 25, 10, 30, 0, tzinfo=UTC)
        cron = croniter("0 * * * *", base)
        prev = cron.get_prev(datetime)
        assert prev == datetime(2026, 4, 25, 10, 0, 0, tzinfo=UTC)

    def test_croniter_get_next_after_prev(self) -> None:
        base = datetime(2026, 4, 25, 10, 15, 0, tzinfo=UTC)
        cron = croniter("*/10 * * * *", base)
        prev = cron.get_prev(datetime)
        nxt = cron.get_next(datetime)
        assert prev == datetime(2026, 4, 25, 10, 10, 0, tzinfo=UTC)
        assert nxt == datetime(2026, 4, 25, 10, 20, 0, tzinfo=UTC)

    def test_croniter_daily(self) -> None:
        base = datetime(2026, 4, 25, 10, 0, 0, tzinfo=UTC)
        cron = croniter("0 9 * * *", base)
        prev = cron.get_prev(datetime)
        assert prev == datetime(2026, 4, 25, 9, 0, 0, tzinfo=UTC)


class TestSchedulerService:
    @pytest.mark.asyncio
    async def test_no_cron_rules_returns_empty(self) -> None:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await schedule_due_rules(mock_session)
        assert isinstance(result, SchedulerResult)
        assert result.checked_rules == 0
        assert result.scheduled == 0
        assert result.skipped == 0
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_schedules_due_rule(self) -> None:
        now = datetime(2026, 4, 25, 10, 5, 0, tzinfo=UTC)
        rule = MagicMock()
        rule.id = "11111111-1111-1111-1111-111111111111"
        rule.datasource_id = "22222222-2222-2222-2222-222222222222"
        rule.cron_expr = "*/5 * * * *"
        rule.schedule_type = "cron"
        rule.enabled = True
        rule.dimension_scope_json = {}
        rule.code = None
        rule.name = "test-rule"

        version = MagicMock()
        version.version_no = 1
        version.query_config_json = {"query": "test", "step": "30s"}
        version.threshold_config_json = {"operator": "gt", "warning": 80}
        rule.versions = [version]

        mock_session = MagicMock()
        rules_result = MagicMock()
        rules_result.scalars.return_value.all.return_value = [rule]
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(side_effect=[rules_result, existing_result])
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        result = await schedule_due_rules(mock_session, now=now)

        assert result.checked_rules == 1
        assert result.scheduled == 1
        assert result.skipped == 0
        assert result.errors == []

        # Verify job was added to session
        mock_session.add.assert_called()
        call_args = mock_session.add.call_args_list
        job_arg = call_args[0][0][0]
        assert job_arg.trigger_type == "scheduled"
        assert job_arg.job_no.startswith("SCHED-")

    @pytest.mark.asyncio
    async def test_skips_already_scheduled_rule(self) -> None:
        now = datetime(2026, 4, 25, 10, 5, 0, tzinfo=UTC)
        rule = MagicMock()
        rule.id = "11111111-1111-1111-1111-111111111111"
        rule.datasource_id = "22222222-2222-2222-2222-222222222222"
        rule.cron_expr = "*/5 * * * *"
        rule.schedule_type = "cron"
        rule.enabled = True
        rule.dimension_scope_json = {}
        rule.code = None
        rule.name = "test-rule"

        version = MagicMock()
        version.version_no = 1
        version.query_config_json = {"query": "test"}
        version.threshold_config_json = {"operator": "gt", "warning": 80}
        rule.versions = [version]

        mock_session = MagicMock()
        rules_result = MagicMock()
        rules_result.scalars.return_value.all.return_value = [rule]
        existing_job = MagicMock()
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = existing_job
        mock_session.execute = AsyncMock(side_effect=[rules_result, existing_result])
        mock_session.commit = AsyncMock()

        result = await schedule_due_rules(mock_session, now=now)

        assert result.checked_rules == 1
        assert result.scheduled == 0
        assert result.skipped == 1
        assert result.errors == []

        # Verify no job was created
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_cron_expression_is_skipped_with_error(self) -> None:
        rule = MagicMock()
        rule.id = "11111111-1111-1111-1111-111111111111"
        rule.cron_expr = "not-a-valid-cron"
        rule.schedule_type = "cron"
        rule.enabled = True

        mock_session = AsyncMock()
        rules_result = MagicMock()
        rules_result.scalars.return_value.all.return_value = [rule]
        mock_session.execute.return_value = rules_result

        result = await schedule_due_rules(mock_session)
        assert result.checked_rules == 1
        assert result.scheduled == 0
        assert len(result.errors) == 1
        assert "invalid cron expression" in result.errors[0]
