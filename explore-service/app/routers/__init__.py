"""Routers package."""

from fastapi import APIRouter

from app.routers.auth import router as auth_router
from app.routers.adapters import router as adapters_router
from app.routers.training_data import router as training_data_router

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router)
api_router.include_router(adapters_router)
api_router.include_router(training_data_router)

__all__ = ["api_router"]
