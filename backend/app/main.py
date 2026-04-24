from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.user import Role, User, UserRole


async def _seed_default_roles() -> None:
    default_roles = [
        ("admin", "Administrator"),
        ("operator", "Operator"),
        ("viewer", "Viewer"),
    ]
    async with AsyncSessionLocal() as session:
        for code, name in default_roles:
            existing = await session.execute(select(Role).where(Role.code == code))
            if existing.scalar_one_or_none() is None:
                session.add(Role(code=code, name=name))
        await session.commit()


async def _seed_default_admin() -> None:
    async with AsyncSessionLocal() as session:
        role_result = await session.execute(select(Role).where(Role.code == "admin"))
        admin_role = role_result.scalar_one_or_none()
        if admin_role is None:
            return

        user_result = await session.execute(
            select(User)
            .options(selectinload(User.role_links))
            .where(User.username == settings.default_admin_username)
        )
        existing = user_result.scalar_one_or_none()
        if existing is not None:
            return

        user = User(
            username=settings.default_admin_username,
            password_hash=hash_password(settings.default_admin_password),
            status="active",
        )
        session.add(user)
        await session.flush()
        session.add(UserRole(user_id=user.id, role_id=admin_role.id))
        await session.commit()

        print(
            f"Default admin user created: "
            f"username={settings.default_admin_username!r}, "
            f"password={settings.default_admin_password!r}"
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    await _seed_default_roles()
    await _seed_default_admin()
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["root"])
async def read_root() -> dict[str, str]:
    return {"message": settings.app_name}

