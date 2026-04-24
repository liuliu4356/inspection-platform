# 巡检平台 (Inspection Platform)

面向 Prometheus 指标和 Elasticsearch 日志的自动化巡检平台。

## 架构

```text
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   客户端    │────▶│  FastAPI (异步)  │────▶│    PostgreSQL    │
└─────────────┘     │   + Celery       │     └──────────────────┘
                    │   (后台任务)     │     ┌──────────────────┐
                    └──────────────────┘────▶│      Redis       │
                                             └──────────────────┘
```

## 技术栈

| 层级 | 技术 |
|------|------|
| API 框架 | FastAPI (Python 3.11+) |
| ORM | SQLAlchemy 2.0 (异步) |
| 数据库 | PostgreSQL 16 |
| 异步队列 | Celery + Redis |
| 认证 | JWT (access + refresh token), bcrypt |
| 数据源 | Prometheus, Elasticsearch |

## 模块状态

| 模块 | 状态 | 版本 |
|------|------|------|
| 数据源 CRUD + 连通性测试 | ✅ 已完成 | 0.1.0 |
| 巡检规则 CRUD + 版本管理 | ✅ 已完成 | 0.1.0 |
| 任务创建 + 执行引擎 | ✅ 已完成 | 0.2.0 |
| 异步调度 (Celery) | ✅ 已完成 | 0.3.0 |
| **用户认证 + 权限控制** | ✅ **已完成** | **0.4.0** |
| 定时任务 (Celery Beat) | 📋 计划中 | - |
| 报告生成 | 📋 计划中 | - |
| 告警通知 | 📋 计划中 | - |
| 前端界面 | 📋 计划中 | - |

## 快速开始

### 前置条件

- Python 3.11+
- Docker（用于 PostgreSQL 和 Redis）
- pip

### 1. 启动本地基础设施

```powershell
docker compose up -d postgres redis
```

### 2. 安装后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

### 3. 配置环境变量

```powershell
cp .env.example .env
# 根据需要编辑 .env，生产环境务必修改 SECRET_KEY
```

### 4. 执行数据库迁移

```powershell
alembic upgrade head
```

### 5. 启动服务

```powershell
uvicorn app.main:app --reload
```

### 6. 访问 API 文档

[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## API 概览

### 认证（v0.4.0）

除 `/auth/*`、`/health` 和 `/` 外，所有 API 端点均需认证。

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/v1/auth/register` | 注册新用户 | 公开 |
| POST | `/api/v1/auth/login` | 登录，获取 JWT | 公开 |
| POST | `/api/v1/auth/refresh` | 刷新 Token | 公开 |
| GET | `/api/v1/auth/me` | 当前用户信息 | 需认证 |

**默认角色**: `admin`（管理员）、`operator`（操作员）、`viewer`（观察者，新用户默认）

| 角色 | 读取 | 写入 | 执行 | 管理 |
|------|------|------|------|------|
| admin | ✅ | ✅ | ✅ | ✅ |
| operator | ✅ | ✅ | ✅ | - |
| viewer | ✅ | - | - | - |

### 数据源

| 方法 | 端点 | 最低角色 |
|------|------|----------|
| GET | `/api/v1/datasources` | viewer |
| POST | `/api/v1/datasources` | operator |
| GET | `/api/v1/datasources/{id}` | viewer |
| PUT | `/api/v1/datasources/{id}` | operator |
| DELETE | `/api/v1/datasources/{id}` | operator |
| POST | `/api/v1/datasources/{id}/test` | operator |

### 规则

| 方法 | 端点 | 最低角色 |
|------|------|----------|
| GET | `/api/v1/rules` | viewer |
| POST | `/api/v1/rules` | operator |
| GET | `/api/v1/rules/{id}` | viewer |
| PUT | `/api/v1/rules/{id}` | operator |
| DELETE | `/api/v1/rules/{id}` | operator |
| GET | `/api/v1/rules/{id}/versions` | viewer |
| POST | `/api/v1/rules/{id}/dry-run` | operator |

### 任务与执行

| 方法 | 端点 | 最低角色 |
|------|------|----------|
| POST | `/api/v1/jobs/manual` | operator |
| GET | `/api/v1/jobs` | viewer |
| GET | `/api/v1/jobs/{id}` | viewer |
| GET | `/api/v1/jobs/{id}/runs` | viewer |
| POST | `/api/v1/jobs/{id}/cancel` | operator |
| POST | `/api/v1/jobs/{id}/execute` | operator |
| POST | `/api/v1/jobs/{id}/dispatch` | operator |
| GET | `/api/v1/runs/{id}` | viewer |
| POST | `/api/v1/runs/{id}/execute` | operator |
| POST | `/api/v1/runs/{id}/dispatch` | operator |
| GET | `/api/v1/runs/{id}/findings` | viewer |

### 健康检查

| 方法 | 端点 |
|------|------|
| GET | `/api/v1/health` |
| GET | `/` |

## 执行模式

- **`execute`**：在 API 进程中立即执行巡检。
- **`dispatch`**：通过 Celery 将任务加入后台队列执行。
- 设置 `CELERY_TASK_ALWAYS_EAGER=true` 可在开发环境中同步执行 Celery 任务。

## 目录结构

```text
inspection-platform/
├── backend/               # FastAPI 后端
│   ├── app/               # 应用代码
│   │   ├── api/           # API 端点
│   │   ├── core/          # 配置、安全、加密
│   │   ├── db/            # 数据库会话
│   │   ├── models/        # SQLAlchemy 模型
│   │   ├── schemas/       # Pydantic 模型
│   │   ├── services/      # 业务逻辑
│   │   └── tasks/         # Celery 任务
│   ├── tests/             # 测试套件
│   └── alembic/           # 数据库迁移
├── docs/process/          # 开发流程文档
├── scripts/               # 发布脚本
└── .github/               # CI 配置
```

## 开发约定

- [开发工作流](docs/process/development-workflow.md)
- [版本管理策略](docs/process/versioning.md)
- [更新日志](CHANGELOG.md)
