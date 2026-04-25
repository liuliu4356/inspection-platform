import enum


class DatasourceType(str, enum.Enum):
    prometheus = "prometheus"
    elasticsearch = "elasticsearch"
    prometheus_multi = "prometheus_multi"


class AuthType(str, enum.Enum):
    none = "none"
    basic = "basic"
    token = "token"
    api_key = "api_key"


class RuleType(str, enum.Enum):
    prometheus = "prometheus"
    elasticsearch = "elasticsearch"


class SeverityLevel(str, enum.Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class ScheduleType(str, enum.Enum):
    manual = "manual"
    cron = "cron"


class TimeRangeType(str, enum.Enum):
    fixed = "fixed"
    relative = "relative"


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"
    cancelled = "cancelled"
    timeout = "timeout"

