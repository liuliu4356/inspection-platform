# 巡检平台 (Inspection Platform) - 全栈项目文档

## 项目概述

面向 Prometheus 指标和 Elasticsearch 日志的自动化巡检平台，参考 promAI (https://github.com/kubehan/PromAI) 设计思路开发。

### 核心特性

- 多数据源支持（Prometheus、Elasticsearch、多集群 Prometheus）
- 灵活的巡检规则配置（支持阈值配置化）
- 自动化定时巡检（Celery Beat + Cron）
- HTML 巡检报告生成
- 服务健康状态看板
- 用户认证与权限控制（RBAC）

---

## 技术架构

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | React 18 + TypeScript |
| 前端 UI | Ant Design 5 |
| 构建工具 | Vite 5 |
| 后端框架 | FastAPI (Python 3.11+) |
| ORM | SQLAlchemy 2.0 (异步) |
| 数据库 | PostgreSQL 16 |
| 任务队列 | Celery + Redis |
| 认证 | JWT + bcrypt |

### 架构图

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   前端界面   │────▶│   FastAPI 后端   │────▶│    PostgreSQL    │
│  (React)    │     │   (异步 API)     │     │     (16)        │
└─────────────┘     └──────────────────┘     └──────────────────┘
                           │
                           ▼
                    ┌──────────────────┐
                    │      Redis       │
                    │  (缓存 + 队列)   │
                    └──────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
        ┌──────────┐             ┌──────────┐
        │  Worker │             │   Beat   │
        │ (执行)  │             │ (调度)  │
        └──────────┘             └──────────┘
```

---

## 项目结构

```
inspection-platform/
├── frontend/                    # React 前端
│   ├── src/
│   │   ├── pages/              # 页面组件
│   │   │   ├── Dashboard.tsx   # 仪表盘（健康看板）
│   │   │   ├── Datasources.tsx # 数据源管理
│   │   │   ├── Rules.tsx       # 规则管理
│   │   │   ├── Jobs.tsx        # 任务管理
│   │   │   ├── JobDetail.tsx   # 任务详情
│   │   │   ├── Users.tsx       # 用户管理
│   │   │   └── Login.tsx       # 登录页
│   │   ├── components/         # 共用组件
│   │   ├── services/          # API 服务
│   │   ├── contexts/         # React Context
│   │   └── types/            # TypeScript 类型
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                     # FastAPI 后端
│   ├── app/
│   │   ├── api/              # API 端点
│   │   │   └── v1/
│   │   │       └── endpoints/
│   │   │           ├── auth.py         # 认证
│   │   │           ├── datasources.py  # 数据源
│   │   │           ├── rules.py      # 规则
│   │   │           ├── jobs.py      # 任务
│   │   │           └── scheduler.py # 调度器
│   │   ├── core/             # 核心配置
│   │   │   ├── config.py      # 配置管理
│   │   │   ├── security.py   # 安全认证
│   │   │   └── crypto.py    # 加密工具
│   │   ├── models/           # 数据模型
│   │   │   ├── user.py       # 用户模型
│   │   │   ├── datasource.py # 数据源模型
│   │   │   ├── rule.py       # 规则模型
│   │   │   ├── job.py       # 任务模型
│   │   │   ├── report.py    # 报告模型
│   │   │   └── enums.py    # 枚举类型
│   │   ├── schemas/          # Pydantic 模型
│   │   ├── services/        # 业务逻辑
│   │   │   ├── job_service.py
│   │   │   ├── inspection_executor.py
│   │   │   ├── datasource_probe.py
│   │   │   ├── scheduler_service.py
│   │   │   └── report_generator.py # HTML报告生成
│   │   └── tasks/           # Celery 任务
│   ├── alembic/            # 数据库迁移
│   └── tests/              # 测试
│
├── docker-compose.yml        # Docker 编排
├── VERSION               # 版本号
└── README.zh-CN.md       # 项目说明
```

---

## 核心模块

### 1. 数据源模块 (Datasource)

支持的数据源类型：

| 类型 | 说明 |
|------|------|
| `prometheus` | 单个 Prometheus 实例 |
| `elasticsearch` | Elasticsearch 集群 |
| `prometheus_multi` | 多 Prometheus 集群（通过 URL 参数切换）|

**新增功能**：多 Prometheus 集群支持
- 创建数据源时支持配置多个集群
- 通过 `datasource` 参数动态切换不同集群
- API: `POST /api/v1/datasources/multi`

### 2. 规则模块 (Rule)

巡检规则配置：

| 字段 | 说明 |
|------|------|
| `name` | 规则名称 |
| `code` | 规则代码 |
| `rule_type` | 规则类型（prometheus/elasticsearch）|
| `datasource_id` | 关联的数据源 |
| `severity` | 严重程度（info/warning/critical）|
| `enabled` | 是否启用 |
| `schedule_type` | 调度类型（manual/cron）|
| `cron_expr` | Cron 表达式 |
| `query_config` | 查询配置 |
| `threshold_config` | 阈值配置 |

**阈值配置结构**：
```json
{
  "thresholds": [
    {
      "name": "CPU使用率",
      "threshold": 80,
      "threshold_type": "greater",
      "threshold_status": "warning",
      "unit": "%"
    }
  ],
  "labels": {
    "instance": "节点"
  }
}
```

### 3. 任务模块 (Job)

任务执行流程：

1. **创建任务**：`POST /api/v1/jobs/manual`
2. **执行任务**：`POST /api/v1/jobs/{id}/execute`（同步）
3. **分发任务**：`POST /api/v1/jobs/{id}/dispatch`（异步）
4. **取消任务**：`POST /api/v1/jobs/{id}/cancel`

任务状态：`pending` → `running` → `success`/`failed`/`cancelled`

### 4. 报告模块 (Report)

**HTML 报告生成**：
- 端点：`GET /api/v1/jobs/{job_id}/report`
- 返回格式：HTML 页面

**���告内容**：
- 任务概览统计
- 成功/失败统计
- 告警级别统计（critical/warning/info）
- 任务执行详情表格
- 严重告警列表

---

## 快速开始

### 前置条件

- Python 3.11+
- Node.js 18+
- Docker Desktop
- PostgreSQL 16
- Redis 7

### 启动方式一：Docker 一键部署

```powershell
# 克隆项目
git clone https://github.com/liuliu4356/inspection-platform.git
cd inspection-platform

# 启动所有服务
docker compose up -d
```

访问地址：
- 前端：http://localhost:8080
- 后端：http://localhost:18000
- API 文档：http://localhost:18000/docs

### 启动方式二：手动部署

```powershell
# 后端
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 18000

# 前端（新终端）
cd frontend
npm install
npm run dev
```

访问地址：
- 前端：http://localhost:3001
- 后端：http://localhost:18000

---

## API 接口文档

### 认证接口

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/login` | 用户登录 |
| POST | `/api/v1/auth/register` | 用户注册 |
| GET | `/api/v1/auth/me` | 当前用户信息 |

### 数据源接口

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/v1/datasources` | 获取数据源列表 |
| POST | `/api/v1/datasources` | 创建数据源 |
| GET | `/api/v1/datasources/{id}` | 获取数据源详情 |
| PUT | `/api/v1/datasources/{id}` | 更新数据源 |
| DELETE | `/api/v1/datasources/{id}` | 删除数据源 |
| POST | `/api/v1/datasources/{id}/test` | 测试数据源连接 |
| POST | `/api/v1/datasources/multi` | 创建多集群数据源 |

### 规则接口

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/v1/rules` | 获取规则列表 |
| POST | `/api/v1/rules` | 创建规则 |
| GET | `/api/v1/rules/{id}` | 获取规则详情 |
| PUT | `/api/v1/rules/{id}` | 更新规则 |
| DELETE | `/api/v1/rules/{id}` | 删除规则 |
| GET | `/api/v1/rules/{id}/versions` | 获取规则版本历史 |
| POST | `/api/v1/rules/{id}/dry-run` | 试运行规则 |

### 任务接口

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/v1/jobs/manual` | 创建手动任务 |
| GET | `/api/v1/jobs` | 获取任务列表 |
| GET | `/api/v1/jobs/{id}` | 获取任务详情 |
| POST | `/api/v1/jobs/{id}/execute` | 执行任务 |
| POST | `/api/v1/jobs/{id}/dispatch` | 分发任务 |
| POST | `/api/v1/jobs/{id}/cancel` | 取消任务 |
| GET | `/api/v1/jobs/{id}/runs` | 获取任务运行记录 |
| GET | `/api/v1/jobs/{id}/report` | 获取 HTML 报告 |

### 调度器接口

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/v1/scheduler/tick` | 手动触发调度检查 |

---

## 用户角色与权限

| 角色 | 说明 | 权限 |
|------|------|------|
| `admin` | 管理员 | 全部权限 |
| `operator` | 操作员 | 读、写、执行 |
| `viewer` | 观察者 | 只读 |

默认账号：
- 用户名：admin
- 密码：admin123

---

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 0.6.0 | 2026-04-25 | 增强 promAI 风格功能 |
| 0.5.0 | - | Celery Beat 定时调度 |
| 0.4.0 | - | 用户认证与 RBAC |
| 0.3.0 | - | 异步任务分发 |
| 0.2.0 | - | 任务执行引擎 |
| 0.1.0 | - | 基础 CRUD 功能 |

---

## 参考项目

- promAI: https://github.com/kubehan/PromAI
  - Go 语言实现的 Prometheus 巡检工具
  - 提供 HTML 报告、服务健康看板
  - 多数据源支持

---

## 常见问题

### Q1: 前端访问端口是多少？

A: 前端开发服务器端口是 **3001**（不是 3000）

### Q2: 如何查看后端日志？

```powershell
docker compose logs -f api
```

### Q3: 如何修改数据库配置？

编辑 `backend/.env` 文件中的 `DATABASE_URL`

### Q4: 如何开启 Celery 异步执行？

设置环境变量 `CELERY_TASK_ALWAYS_EAGER=false`

---

## 许可证

MIT License

## 作者

- GitHub: https://github.com/liuliu4356