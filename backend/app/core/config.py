from functools import lru_cache

from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="Inspection Platform API", alias="APP_NAME")
    debug: bool = Field(default=False, alias="DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/inspection_platform",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://127.0.0.1:6379/0", alias="REDIS_URL")
    fernet_key: str = Field(
        default="YvMY4dWbJ9K8Q4p4fiI7T-4vI4D1vS0mTgIYbK0lF5A=",
        alias="FERNET_KEY",
    )
    http_timeout_seconds: int = Field(default=10, alias="HTTP_TIMEOUT_SECONDS")

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "dev", "development"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False
        return bool(value)

    @property
    def database_url_sync(self) -> str:
        return self.database_url.replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
