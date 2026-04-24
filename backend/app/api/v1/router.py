from fastapi import APIRouter

from app.api.v1.endpoints import datasources, health, jobs, rules

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(datasources.router)
api_router.include_router(rules.router)
api_router.include_router(jobs.router)
