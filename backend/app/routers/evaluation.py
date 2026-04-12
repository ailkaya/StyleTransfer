"""API routes for evaluation."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response as FastAPIResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel

from ..models import get_db, Task
from ..schemas import Response
from ..services import evaluation_service, get_inference_service

router = APIRouter(prefix="/api/tasks", tags=["evaluation"])


class EvaluationData(BaseModel):
    """Evaluation metrics data for frontend."""
    task_id: str
    task_name: str
    target_style: str
    generated_at: str

    # Overall metrics
    overall_score: float
    sample_count: int

    # Detailed metrics
    semantic_score: float
    char_retention: float
    style_score: float
    fluency_score: float
    vocab_diversity: float
    length_ratio: float
    avg_response_time: float

    # Sample pairs for comparison
    samples: list[dict]


class EvaluationResponse(Response):
    """Evaluation response with data."""
    data: Optional[EvaluationData] = None


@router.get("/{task_id}/evaluation", response_model=EvaluationResponse)
async def get_evaluation(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get evaluation report data for a completed task."""
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

    # Get inference service for generating samples
    inference_service = get_inference_service()

    # Generate evaluation data
    # evaluation_data = await evaluation_service.generate_evaluation_data(
    #     task_id=task_id,
    #     inference_service=inference_service
    # )
    evaluation_data = evaluation_service.get_mock_evaluation_data(task_id=task_id)

    return EvaluationResponse(
        code=200,
        message="success",
        data=evaluation_data,
        timestamp=datetime.utcnow(),
    )
