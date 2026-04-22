"""API routes for system monitoring."""

from datetime import datetime
from fastapi import APIRouter

from ..schemas import Response
from ..services.monitoring import monitoring_service
from ..utils import get_logger

router = APIRouter(prefix="/api/system", tags=["system"])
logger = get_logger(__name__)


@router.get("/stats", response_model=Response)
async def get_system_stats():
    """Get real-time system monitoring statistics (CPU, memory, GPU)."""
    logger.debug("Fetching system stats")
    stats = monitoring_service.get_all_stats()
    return Response(
        code=200,
        message="success",
        data=stats,
        timestamp=datetime.utcnow(),
    )
