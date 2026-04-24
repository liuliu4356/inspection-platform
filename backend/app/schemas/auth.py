from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMBaseModel, TimestampedReadModel


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=6, max_length=128)
    email: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class RoleRead(ORMBaseModel):
    id: UUID
    code: str
    name: str


class UserRead(TimestampedReadModel):
    username: str
    email: str | None
    status: str
    roles: list[RoleRead] = Field(default_factory=list)
