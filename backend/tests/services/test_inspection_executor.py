from types import SimpleNamespace

from app.models.enums import SeverityLevel
from app.services.inspection_executor import (
    _summarize_elasticsearch_result,
    _summarize_prometheus_result,
    evaluate_threshold,
)


def test_summarize_prometheus_matrix_uses_requested_aggregation() -> None:
    result = _summarize_prometheus_result(
        {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {"__name__": "cpu_usage", "instance": "node-1"},
                    "values": [[1714010000, "42"], [1714010060, "88"]],
                },
                {
                    "metric": {"__name__": "cpu_usage", "instance": "node-2"},
                    "values": [[1714010000, "51"]],
                },
            ],
        },
        aggregation="max",
    )

    assert result.observed_value == 88.0
    assert result.metric_name == "cpu_usage"
    assert result.summary["series_count"] == 2
    assert result.summary["sample_count"] == 3


def test_summarize_elasticsearch_defaults_to_total_hits() -> None:
    result = _summarize_elasticsearch_result(
        {
            "took": 17,
            "timed_out": False,
            "hits": {"total": {"value": 23, "relation": "eq"}},
        },
        threshold_config={},
    )

    assert result.observed_value == 23.0
    assert result.summary["total_hits"] == 23


def test_summarize_elasticsearch_supports_value_path() -> None:
    result = _summarize_elasticsearch_result(
        {
            "hits": {"total": {"value": 10, "relation": "eq"}},
            "aggregations": {
                "error_rate": {"value": 3.14},
            },
        },
        threshold_config={"value_path": "aggregations.error_rate.value"},
    )

    assert result.observed_value == 3.14


def test_evaluate_threshold_uses_rule_severity_for_single_threshold() -> None:
    rule = SimpleNamespace(severity=SeverityLevel.warning)

    evaluation = evaluate_threshold(
        rule=rule,
        observed_value=81.0,
        threshold_config={"threshold": 80, "operator": "gt"},
    )

    assert evaluation.severity == SeverityLevel.warning
    assert evaluation.finding_required is True


def test_evaluate_threshold_flags_missing_numeric_value_when_requested() -> None:
    rule = SimpleNamespace(severity=SeverityLevel.critical)

    evaluation = evaluate_threshold(
        rule=rule,
        observed_value=None,
        threshold_config={"fail_on_no_value": True},
    )

    assert evaluation.severity == SeverityLevel.warning
    assert evaluation.finding_required is True

