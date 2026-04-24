from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(_: FastAPI):
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

