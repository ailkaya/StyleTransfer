"""API routes for evaluation."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel

from ..models import get_db, Task, Evaluation
from ..schemas import Response

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
    """Get evaluation report data from evaluations table for a completed task."""
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

    # Check if task is still evaluating
    if task.status == "EVALUATING":
        return EvaluationResponse(
            code=200,
            message="evaluating",
            data=None,
            timestamp=datetime.utcnow(),
        )

    # Check if task is completed but evaluation not done
    if task.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task status is {task.status}, evaluation not available"
        )

    # Query evaluation from separate table
    eval_result = await db.execute(
        select(Evaluation).where(Evaluation.task_id == task_id)
    )
    evaluation = eval_result.scalar_one_or_none()

    if evaluation:
        # Return evaluation data from database
        return EvaluationResponse(
            code=200,
            message="success",
            data=evaluation.to_dict(),
            timestamp=datetime.utcnow(),
        )
    else:
        # Task completed but no evaluation record found
        # Return empty/default data
        return EvaluationResponse(
            code=200,
            message="success",
            data={
                "task_id": str(task_id),
                "task_name": task.name or "未命名任务",
                "target_style": "未知",
                "generated_at": task.completed_at.strftime('%Y-%m-%d %H:%M') if task.completed_at else "-",
                "overall_score": 0,
                "sample_count": 0,
                "semantic_score": 0,
                "char_retention": 0,
                "style_score": 0,
                "fluency_score": 0,
                "vocab_diversity": 0,
                "length_ratio": 0,
                "avg_response_time": 0,
                "samples": []
            },
            timestamp=datetime.utcnow(),
        )
