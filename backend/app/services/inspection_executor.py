from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from statistics import fmean
from typing import Any

import httpx

from app.models.datasource import Datasource
from app.models.enums import DatasourceType, SeverityLevel
from app.models.rule import InspectionRule
from app.services.datasource_probe import build_headers_and_auth


SUPPORTED_OPERATORS = {"gt", "gte", "lt", "lte", "eq", "ne"}
SUPPORTED_AGGREGATIONS = {
    "avg",
    "count",
    "first",
    "last",
    "max",
    "min",
    "sample_count",
    "series_count",
    "sum",
}


@dataclass(slots=True)
class ExecutionQueryResult:
    observed_value: float | None
    summary: dict[str, Any]
    metric_name: str | None = None
    labels: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvaluationResult:
    observed_value: float | None
    severity: SeverityLevel
    finding_required: bool
    message: str
    threshold_snapshot: dict[str, Any]


def _coerce_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _default_prometheus_step(range_start: datetime, range_end: datetime) -> str:
    duration_seconds = max(int((range_end - range_start).total_seconds()), 1)
    step_seconds = max(duration_seconds // 120, 15)
    return f"{step_seconds}s"


def _extract_json_path(payload: Any, path: str | None) -> Any:
    if not path:
        return payload

    current = payload
    for part in path.split("."):
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _find_first_numeric_value(payload: Any) -> float | None:
    if isinstance(payload, (int, float)):
        return float(payload)
    if isinstance(payload, dict):
        for value in payload.values():
            found = _find_first_numeric_value(value)
            if found is not None:
                return found
    if isinstance(payload, list):
        for value in payload:
            found = _find_first_numeric_value(value)
            if found is not None:
                return found
    return None


def _reduce_values(values: list[float], aggregation: str, *, series_count: int) -> float | None:
    if aggregation not in SUPPORTED_AGGREGATIONS:
        raise ValueError(f"Unsupported aggregation: {aggregation}")

    if aggregation == "series_count":
        return float(series_count)
    if aggregation == "sample_count":
        return float(len(values))
    if aggregation == "count":
        return float(len(values))
    if not values:
        return None
    if aggregation == "first":
        return values[0]
    if aggregation == "last":
        return values[-1]
    if aggregation == "max":
        return max(values)
    if aggregation == "min":
        return min(values)
    if aggregation == "sum":
        return float(sum(values))
    if aggregation == "avg":
        return float(fmean(values))
    raise ValueError(f"Unsupported aggregation: {aggregation}")


def _summarize_prometheus_result(data: dict[str, Any], aggregation: str) -> ExecutionQueryResult:
    result_type = data.get("resultType")
    result = data.get("result", [])
    numeric_values: list[float] = []
    series_count = 0
    metric_name: str | None = None
    labels: dict[str, Any] = {}

    if result_type == "matrix":
        series_count = len(result)
        for item in result:
            metric = item.get("metric", {})
            if metric and not metric_name:
                metric_name = metric.get("__name__")
                labels = {key: value for key, value in metric.items() if key != "__name__"}
            for timestamp, value in item.get("values", []):
                del timestamp
                numeric_values.append(float(value))
    elif result_type == "vector":
        series_count = len(result)
        for item in result:
            metric = item.get("metric", {})
            if metric and not metric_name:
                metric_name = metric.get("__name__")
                labels = {key: value for key, value in metric.items() if key != "__name__"}
            value = item.get("value", [None, None])[1]
            if value is not None:
                numeric_values.append(float(value))
    elif result_type == "scalar":
        value = result[1] if isinstance(result, list) and len(result) >= 2 else None
        if value is not None:
            numeric_values.append(float(value))
    else:
        raise ValueError(f"Unsupported Prometheus result type: {result_type}")

    observed_value = _reduce_values(numeric_values, aggregation, series_count=series_count)
    summary = {
        "result_type": result_type,
        "series_count": series_count,
        "sample_count": len(numeric_values),
        "aggregation": aggregation,
        "observed_value": observed_value,
        "preview_values": numeric_values[:10],
    }
    return ExecutionQueryResult(
        observed_value=observed_value,
        summary=summary,
        metric_name=metric_name,
        labels=labels,
    )


def _summarize_elasticsearch_result(payload: dict[str, Any], threshold_config: dict[str, Any]) -> ExecutionQueryResult:
    value_path = threshold_config.get("value_path")
    aggregation = threshold_config.get("aggregation", "hits_total")
    observed_value: float | None = None

    if value_path:
        extracted = _extract_json_path(payload, value_path)
        if extracted is not None:
            observed_value = float(extracted)
    elif aggregation == "hits_total":
        observed_value = float(payload.get("hits", {}).get("total", {}).get("value", 0))
    else:
        observed_value = _find_first_numeric_value(payload.get("aggregations", {}))

    total_hits = payload.get("hits", {}).get("total", {}).get("value", 0)
    summary = {
        "took": payload.get("took"),
        "timed_out": payload.get("timed_out", False),
        "total_hits": total_hits,
        "aggregation": aggregation,
        "value_path": value_path,
        "observed_value": observed_value,
    }
    return ExecutionQueryResult(observed_value=observed_value, summary=summary)


def _compare(left: float, right: float, operator: str) -> bool:
    if operator not in SUPPORTED_OPERATORS:
        raise ValueError(f"Unsupported operator: {operator}")
    if operator == "gt":
        return left > right
    if operator == "gte":
        return left >= right
    if operator == "lt":
        return left < right
    if operator == "lte":
        return left <= right
    if operator == "eq":
        return left == right
    return left != right


def evaluate_threshold(
    *,
    rule: InspectionRule,
    observed_value: float | None,
    threshold_config: dict[str, Any],
) -> EvaluationResult:
    operator = threshold_config.get("operator", "gt")
    critical_threshold = threshold_config.get("critical")
    warning_threshold = threshold_config.get("warning")
    threshold = threshold_config.get("threshold")

    if threshold is not None and critical_threshold is None and warning_threshold is None:
        if rule.severity == SeverityLevel.critical:
            critical_threshold = threshold
        elif rule.severity == SeverityLevel.warning:
            warning_threshold = threshold

    if observed_value is None:
        severity = SeverityLevel.warning if threshold_config.get("fail_on_no_value") else SeverityLevel.info
        message = "Query succeeded but no numeric value could be derived from the result"
        return EvaluationResult(
            observed_value=None,
            severity=severity,
            finding_required=severity != SeverityLevel.info,
            message=message,
            threshold_snapshot={
                "operator": operator,
                "warning": warning_threshold,
                "critical": critical_threshold,
            },
        )

    severity = SeverityLevel.info
    message = "Observed value is within the configured threshold range"
    if critical_threshold is not None and _compare(observed_value, float(critical_threshold), operator):
        severity = SeverityLevel.critical
        message = (
            f"Observed value {observed_value} matched critical threshold "
            f"{operator} {critical_threshold}"
        )
    elif warning_threshold is not None and _compare(observed_value, float(warning_threshold), operator):
        severity = SeverityLevel.warning
        message = (
            f"Observed value {observed_value} matched warning threshold "
            f"{operator} {warning_threshold}"
        )

    return EvaluationResult(
        observed_value=observed_value,
        severity=severity,
        finding_required=severity != SeverityLevel.info,
        message=message,
        threshold_snapshot={
            "operator": operator,
            "warning": warning_threshold,
            "critical": critical_threshold,
        },
    )


async def execute_query_snapshot(
    *,
    datasource: Datasource,
    query_snapshot: dict[str, Any],
    auth_config: dict[str, Any],
    timeout_seconds: int,
) -> ExecutionQueryResult:
    headers, auth = build_headers_and_auth(datasource.auth_type, auth_config)
    verify_tls = datasource.extra_config_json.get("verify_tls", True)
    query_config = query_snapshot.get("query_config", {})
    threshold_config = query_snapshot.get("threshold_config", {})

    async with httpx.AsyncClient(
        timeout=timeout_seconds,
        verify=verify_tls,
        headers=headers,
        auth=auth,
    ) as client:
        if datasource.type == DatasourceType.prometheus:
            range_start = _coerce_datetime(query_snapshot["range_start"])
            range_end = _coerce_datetime(query_snapshot["range_end"])
            step = query_config.get("step") or _default_prometheus_step(range_start, range_end)
            response = await client.post(
                datasource.endpoint.rstrip("/") + "/api/v1/query_range",
                data={
                    "query": query_config["query"],
                    "start": range_start.isoformat(),
                    "end": range_end.isoformat(),
                    "step": step,
                },
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("status") != "success":
                raise ValueError("Prometheus API returned a non-success status")
            result = _summarize_prometheus_result(
                payload.get("data", {}),
                aggregation=threshold_config.get("aggregation", "max"),
            )
            result.summary.update({"query": query_config["query"], "step": step})
            return result

        if datasource.type == DatasourceType.elasticsearch:
            request_body = {
                key: value
                for key, value in query_config.items()
                if key not in {"index", "indices"}
            }
            request_body.setdefault("track_total_hits", True)
            index = query_config.get("index") or query_config.get("indices")
            search_path = "/_search"
            if index:
                if isinstance(index, list):
                    index = ",".join(index)
                search_path = f"/{index}/_search"
            response = await client.post(datasource.endpoint.rstrip("/") + search_path, json=request_body)
            response.raise_for_status()
            payload = response.json()
            result = _summarize_elasticsearch_result(payload, threshold_config)
            result.summary.update({"index": index, "query_keys": sorted(request_body.keys())})
            return result

    raise ValueError(f"Unsupported datasource type: {datasource.type.value}")
