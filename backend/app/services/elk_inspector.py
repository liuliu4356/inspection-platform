"""ELK 巡检执行器"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any
import yaml
import httpx


class ELKClient:
    """Elasticsearch 客户端"""

    def __init__(self, url: str, username: str = "", password: str = ""):
        self.url = url.rstrip("/")
        self.username = username
        self.password = password

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{self.url}/{path}"
            auth = (self.username, self.password) if self.username else None
            response = await client.request(method, url, auth=auth, **kwargs)
            response.raise_for_status()
            return response.json()

    async def cluster_health(self) -> dict:
        """获取集群健康状态"""
        return await self._request("GET", "_cluster/health")

    async def cluster_stats(self) -> dict:
        """获取集群统计信息"""
        return await self._request("GET", "_cluster/stats")

    async def nodes_stats(self) -> dict:
        """获取节点统计"""
        return await self._request("GET", "_nodes/stats")

    async def indices_stats(self, index: str = "*") -> dict:
        """获取索引统计"""
        return await self._request("GET", f"{index}/_stats")

    async def cat_indices(self) -> dict:
        """获取索引列表"""
        return await self._request("GET", "_cat/indices?format=json")

    async def cat_nodes(self) -> dict:
        """获取节点列表"""
        return await self._request("GET", "_cat/nodes?format=json")

    async def search(self, index: str, body: dict) -> dict:
        """搜索"""
        return await self._request("POST", f"{index}/_search", json=body)


class ELKInspectionResult:
    """ELK 巡检结果"""

    def __init__(self):
        self.cluster_name: str = ""
        self.status: str = "unknown"
        self.timestamp: datetime = datetime.now()
        self.metrics: list[dict] = []
        self.warnings: list[dict] = []
        self.critical: list[dict] = []
        self.normal: list[dict] = []

    def add_metric(
        self,
        name: str,
        value: Any,
        threshold: float,
        threshold_type: str,
        threshold_status: str,
        unit: str = "",
    ) -> None:
        status = self._evaluate(value, threshold, threshold_type)
        metric = {
            "name": name,
            "value": value,
            "threshold": threshold,
            "threshold_type": threshold_type,
            "threshold_status": threshold_status,
            "status": status,
            "unit": unit,
        }
        self.metrics.append(metric)

        if status == "critical":
            self.critical.append(metric)
        elif status == "warning":
            self.warnings.append(metric)
        else:
            self.normal.append(metric)

    def _evaluate(self, value: Any, threshold: float, threshold_type: str) -> str:
        try:
            if threshold_type == "greater":
                return "critical" if float(value) >= float(threshold) else "normal"
            elif threshold_type == "less":
                return "critical" if float(value) <= float(threshold) else "normal"
            elif threshold_type == "equal":
                return "normal" if str(value) == str(threshold) else "warning"
            elif threshold_type == "not_equal":
                return "normal" if str(value) != str(threshold) else "warning"
            return "normal"
        except (ValueError, TypeError):
            return "normal"

    def to_dict(self) -> dict:
        return {
            "cluster_name": self.cluster_name,
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
            "metrics": self.metrics,
            "warnings": self.warnings,
            "critical": self.critical,
            "normal": self.normal,
            "summary": {
                "total": len(self.metrics),
                "normal": len(self.normal),
                "warning": len(self.warnings),
                "critical": len(self.critical),
            },
        }


class ELKInspectionExecutor:
    """ELK 巡检执行器"""

    def __init__(self, config_path: str = "config/elk_inspection.yaml"):
        self.config_path = config_path
        self.config: dict = {}
        self._load_config()

    def _load_config(self) -> None:
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            self.config = {}

    async def inspect(self, elk_url: str, username: str = "", password: str = "") -> ELKInspectionResult:
        """执行 ELK 巡检"""
        client = ELKClient(elk_url, username, password)
        result = ELKInspectionResult()

        try:
            # 获取集群健康状态
            health = await client.cluster_health()
            result.cluster_name = health.get("cluster_name", "unknown")
            result.status = health.get("status", "unknown")

            # 检查集群状态
            status = result.status
            result.add_metric(
                "集群健康状态",
                status,
                threshold="green",
                threshold_type="equal",
                threshold_status="normal",
            )

            # 获取节点统计
            nodes_stats = await client.nodes_stats()
            nodes = nodes_stats.get("nodes", {})

            # 检查节点数量
            num_nodes = len(nodes)
            result.add_metric(
                "节点数量",
                num_nodes,
                threshold=3,
                threshold_type="greater",
                threshold_status="warning",
            )

            # 检查节点 JVM 内存
            for node_id, node_data in nodes.items():
                jvm = node_data.get("jvm", {})
                if jvm:
                    mem = jvm.get("mem", {})
                    heap_used = mem.get("heap_used_percent", 0)
                    result.add_metric(
                        f"节点 {node_id[:8]} JVM 堆内存使用率",
                        heap_used,
                        threshold=85,
                        threshold_type="greater",
                        threshold_status="warning",
                        unit="%",
                    )

                # CPU 使用率
                process = node_data.get("process", {})
                cpu_percent = process.get("cpu", {}).get("percent", 0)
                result.add_metric(
                    f"节点 {node_id[:8]} CPU 使用率",
                    cpu_percent,
                    threshold=80,
                    threshold_type="greater",
                    threshold_status="warning",
                    unit="%",
                )

            # 获取索引统计
            indices_stats = await client.indices_stats()
            total_docs = indices_stats.get("_all", {}).get("primaries", {}).get("docs", {}).get("count", 0)
            total_size = indices_stats.get("_all", {}).get("store", {}).get("size_in_bytes", 0)

            result.add_metric(
                "索引文档总数",
                total_docs,
                threshold=100000000,
                threshold_type="greater",
                threshold_status="warning",
            )

            result.add_metric(
                "索引总大小",
                total_size / (1024**3),
                threshold=100,
                threshold_type="greater",
                threshold_status="warning",
                unit="GB",
            )

            # 获取集群统计
            cluster_stats = await client.cluster_stats()
            shards = cluster_stats.get("_shards", {})
            result.add_metric(
                "未分配分片",
                shards.get("unassigned", 0),
                threshold=0,
                threshold_type="equal",
                threshold_status="normal",
            )

        except Exception as e:
            result.status = "error"
            result.add_metric(
                "巡检执行",
                str(e),
                threshold=0,
                threshold_type="equal",
                threshold_status="critical",
            )

        return result

    async def inspect_all_clusters(self) -> list[ELKInspectionResult]:
        """巡检所有启用的集群"""
        results = []
        elk_clusters = self.config.get("elk_clusters", [])

        for cluster in elk_clusters:
            if not cluster.get("enabled", True):
                continue

            result = await self.inspect(
                cluster.get("url", ""),
                cluster.get("username", ""),
                cluster.get("password", ""),
            )
            results.append(result)

        return results


async def run_elk_inspection(config_path: str = "config/elk_inspection.yaml") -> list[dict]:
    """运行 ELK 巡检（CLI 入口）"""
    executor = ELKInspectionExecutor(config_path)
    results = await executor.inspect_all_clusters()
    return [r.to_dict() for r in results]


if __name__ == "__main__":
    import json

    async def main():
        results = await run_elk_inspection()
        print(json.dumps(results, indent=2, ensure_ascii=False))

    asyncio.run(main())