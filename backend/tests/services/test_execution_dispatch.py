from app.services.execution_dispatch import _next_eager_task_id, build_dispatch_record


def test_build_dispatch_record_contains_expected_fields() -> None:
    record = build_dispatch_record(
        task_id="task-123",
        queue="inspection",
        execution_mode="queued",
    )

    assert record["task_id"] == "task-123"
    assert record["queue"] == "inspection"
    assert record["execution_mode"] == "queued"
    assert "queued_at" in record


def test_eager_task_id_uses_prefix() -> None:
    task_id = _next_eager_task_id("job")

    assert task_id.startswith("job-eager-")

