"""Routers package."""

from fastapi import APIRouter

from .styles import router as styles_router
from .tasks import router as tasks_router
from .messages import router as messages_router
from .config import router as config_router
from .evaluation import router as evaluation_router

# Create main API router
api_router = APIRouter()

# Include all routers
api_router.include_router(styles_router)
api_router.include_router(tasks_router)
api_router.include_router(messages_router)
api_router.include_router(config_router)
api_router.include_router(evaluation_router)

__all__ = ["api_router"]
