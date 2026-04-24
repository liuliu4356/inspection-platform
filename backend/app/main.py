from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.user import Role


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


@asynccontextmanager
async def lifespan(_: FastAPI):
    await _seed_default_roles()
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

