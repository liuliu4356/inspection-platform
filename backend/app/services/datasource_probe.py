from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.models.enums import AuthType, DatasourceType


@dataclass(slots=True)
class ProbeResult:
    success: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


def _build_headers(auth_type: AuthType, auth_config: dict[str, Any]) -> tuple[dict[str, str], httpx.BasicAuth | None]:
    headers: dict[str, str] = {}
    auth: httpx.BasicAuth | None = None

    if auth_type == AuthType.basic:
        username = auth_config.get("username")
        password = auth_config.get("password")
        if username and password:
            auth = httpx.BasicAuth(username, password)
    elif auth_type == AuthType.token:
        token = auth_config.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_type == AuthType.api_key:
        encoded = auth_config.get("encoded")
        if not encoded:
            key_id = auth_config.get("id")
            api_key = auth_config.get("api_key")
            if key_id and api_key:
                encoded = base64.b64encode(f"{key_id}:{api_key}".encode("utf-8")).decode("utf-8")
        if encoded:
            headers["Authorization"] = f"ApiKey {encoded}"

    return headers, auth


async def probe_datasource(
    *,
    datasource_type: DatasourceType,
    endpoint: str,
    auth_type: AuthType,
    auth_config: dict[str, Any],
    extra_config: dict[str, Any],
    timeout_seconds: int,
) -> ProbeResult:
    headers, auth = _build_headers(auth_type, auth_config)
    verify_tls = extra_config.get("verify_tls", True)

    async with httpx.AsyncClient(
        timeout=timeout_seconds,
        verify=verify_tls,
        headers=headers,
        auth=auth,
    ) as client:
        if datasource_type == DatasourceType.prometheus:
            url = endpoint.rstrip("/") + "/api/v1/query"
            response = await client.get(url, params={"query": "1"})
            response.raise_for_status()
            payload = response.json()
            status = payload.get("status")
            if status != "success":
                return ProbeResult(False, "Prometheus query API returned a non-success status", payload)
            return ProbeResult(
                True,
                "Prometheus datasource is reachable",
                {"status": status, "resultType": payload.get("data", {}).get("resultType")},
            )

        if datasource_type == DatasourceType.elasticsearch:
            url = endpoint.rstrip("/") + "/"
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()
            cluster_name = payload.get("cluster_name")
            version = payload.get("version", {}).get("number")
            return ProbeResult(
                True,
                "Elasticsearch datasource is reachable",
                {"cluster_name": cluster_name, "version": version},
            )

    return ProbeResult(False, f"Unsupported datasource type: {datasource_type.value}")

