"""API routes for evaluation."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Response as FastAPIResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models import get_db, Task
from ..schemas import Response
from ..services import evaluation_service

router = APIRouter(prefix="/api/tasks", tags=["evaluation"])


@router.get("/{task_id}/evaluation")
async def get_evaluation(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get evaluation report HTML for a completed task."""
    # Verify task exists
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id '{task_id}' not found"
        )

    # Generate HTML report
    html_content = evaluation_service.generate_evaluation_html(task_id)

    return FastAPIResponse(
        content=html_content,
        media_type="text/html",
    )
