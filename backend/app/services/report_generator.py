from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def generate_html_report(
    session: AsyncSession,
    job_id: uuid.UUID,
) -> str:
    from app.models.job import InspectionJob, InspectionTaskRun
    from app.models.report import InspectionReport

    job = await session.get(InspectionJob, job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    result = await session.execute(
        select(InspectionTaskRun).where(InspectionTaskRun.job_id == job_id)
    )
    runs = result.scalars().all()

    stats = {
        "total": len(runs),
        "success": sum(1 for r in runs if r.status.value == "success"),
        "failed": sum(1 for r in runs if r.status.value == "failed"),
        "running": sum(1 for r in runs if r.status.value == "running"),
        "pending": sum(1 for r in runs if r.status.value == "pending"),
    }

    severity_stats = {
        "info": sum(1 for r in runs if r.severity and r.severity.value == "info"),
        "warning": sum(1 for r in runs if r.severity and r.severity.value == "warning"),
        "critical": sum(1 for r in runs if r.severity and r.severity.value == "critical"),
    }

    findings_by_severity = {"critical": [], "warning": [], "info": []}
    for run in runs:
        for finding in run.findings:
            if finding.severity:
                findings_by_severity[finding.severity.value].append(finding)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>巡检报告 - {job.job_no}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .header h1 {{ margin: 0 0 10px; color: #333; }}
        .meta {{ color: #666; font-size: 14px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin-bottom: 20px; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 8px; text-align: center; }}
        .stat-value {{ font-size: 32px; font-weight: bold; }}
        .stat-label {{ color: #666; margin-top: 8px; }}
        .stat-total {{ color: #1890ff; }}
        .stat-success {{ color: #52c41a; }}
        .stat-failed {{ color: #ff4d4f; }}
        .stat-running {{ color: #1890ff; }}
        .section {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .section h2 {{ margin: 0 0 16px; padding-bottom: 12px; border-bottom: 1px solid #f0f0f0; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #f0f0f0; }}
        th {{ background: #fafafa; font-weight: 500; }}
        .severity-critical {{ color: #ff4d4f; }}
        .severity-warning {{ color: #faad14; }}
        .severity-info {{ color: #1890ff; }}
        .status-success {{ color: #52c41a; }}
        .status-failed {{ color: #ff4d4f; }}
        .status-running {{ color: #1890ff; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>巡检报告 - {job.job_no}</h1>
            <div class="meta">
                <span>触发类型: {job.trigger_type}</span> |
                <span>状态: {job.status.value}</span> |
                <span>时间范围: {job.range_start.strftime('%Y-%m-%d %H:%M')} ~ {job.range_end.strftime('%Y-%m-%d %H:%M')}</span>
            </div>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-value stat-total">{stats['total']}</div>
                <div class="stat-label">总任务数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value stat-success">{stats['success']}</div>
                <div class="stat-label">成功</div>
            </div>
            <div class="stat-card">
                <div class="stat-value stat-failed">{stats['failed']}</div>
                <div class="stat-label">失败</div>
            </div>
            <div class="stat-card">
                <div class="stat-value stat-running">{stats['running']}</div>
                <div class="stat-label">运行中</div>
            </div>
        </div>

        <div class="section">
            <h2>告警统计</h2>
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value severity-critical">{severity_stats['critical']}</div>
                    <div class="stat-label">严重</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value severity-warning">{severity_stats['warning']}</div>
                    <div class="stat-label">警告</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value severity-info">{severity_stats['info']}</div>
                    <div class="stat-label">信息</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>任务执行详情</h2>
            <table>
                <thead>
                    <tr>
                        <th>规则名称</th>
                        <th>状态</th>
                        <th>严重程度</th>
                        <th>得分</th>
                        <th>开始时间</th>
                        <th>完成时间</th>
                    </tr>
                </thead>
                <tbody>
"""
    for run in runs:
        started = run.started_at.strftime('%Y-%m-%d %H:%M:%S') if run.started_at else '-'
        finished = run.finished_at.strftime('%Y-%m-%d %H:%M:%S') if run.finished_at else '-'
        severity = run.severity.value if run.severity else '-'
        score = f"{run.score:.2f}" if run.score else '-'
        html += f"""
                    <tr>
                        <td>{run.rule.name if run.rule else '-'}</td>
                        <td class="status-{run.status.value}">{run.status.value}</td>
                        <td class="severity-{severity}">{severity}</td>
                        <td>{score}</td>
                        <td>{started}</td>
                        <td>{finished}</td>
                    </tr>
"""
    html += """
                </tbody>
            </table>
        </div>
"""
    if findings_by_severity["critical"]:
        html += """
        <div class="section">
            <h2 class="severity-critical">严重告警</h2>
            <table>
                <thead>
                    <tr>
                        <th>标题</th>
                        <th>指标</th>
                        <th>消息</th>
                    </tr>
                </thead>
                <tbody>
"""
        for f in findings_by_severity["critical"]:
            html += f"""
                    <tr>
                        <td>{f.title}</td>
                        <td>{f.metric_name or '-'}</td>
                        <td>{f.message or '-'}</td>
                    </tr>
"""
        html += """
                </tbody>
            </table>
        </div>
"""
    html += """
    </div>
</body>
</html>
"""
    return html