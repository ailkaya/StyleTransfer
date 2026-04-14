"""API routes for evaluation."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, Field

from ..models import get_db, Task, Evaluation
from ..schemas import Response
from ..utils import get_logger

router = APIRouter(prefix="/api/tasks", tags=["evaluation"])
logger = get_logger(__name__)


class CommentCreate(BaseModel):
    """Comment create/update request."""
    comment: str = Field(..., min_length=1, max_length=2000, description="用户评价内容")


class CommentResponse(Response):
    """Comment response with data."""
    data: Optional[dict] = None


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
    # semantic_score: float
    char_retention: float
    style_score: float
    fluency_score: float
    vocab_diversity: float
    length_ratio: float
    bleu_score: float
    avg_response_time: float

    # Sample pairs for comparison
    samples: list[dict]

    # User comment
    comment: Optional[str] = None


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
                # "semantic_score": 0,
                "char_retention": 0,
                "style_score": 0,
                "fluency_score": 0,
                "vocab_diversity": 0,
                "length_ratio": 0,
                "bleu_score": 0,
                "avg_response_time": 0,
                "comment": None,
                "samples": []
            },
            timestamp=datetime.utcnow(),
        )


@router.post("/{task_id}/comment", response_model=CommentResponse)
async def create_comment(
    task_id: str,
    comment_data: CommentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create or update comment for an evaluation."""
    logger.info(f"Creating/updating comment for task: {task_id}")

    # Verify task exists
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        logger.warning(f"Task not found: {task_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id '{task_id}' not found"
        )

    # Query evaluation from table
    eval_result = await db.execute(
        select(Evaluation).where(Evaluation.task_id == task_id)
    )
    evaluation = eval_result.scalar_one_or_none()

    if not evaluation:
        logger.warning(f"Evaluation not found for task: {task_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation for task '{task_id}' not found"
        )

    # Update comment
    evaluation.comment = comment_data.comment
    await db.commit()
    await db.refresh(evaluation)

    logger.info(f"Comment updated for evaluation: {evaluation.id}")

    return CommentResponse(
        code=200,
        message="评价提交成功",
        data={
            "task_id": str(task_id),
            "evaluation_id": str(evaluation.id),
            "comment": evaluation.comment
        },
        timestamp=datetime.utcnow(),
    )


@router.put("/{task_id}/comment", response_model=CommentResponse)
async def update_comment(
    task_id: str,
    comment_data: CommentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Update comment for an evaluation (alias for create)."""
    logger.info(f"Updating comment for task: {task_id}")
    return await create_comment(task_id, comment_data, db)


@router.get("/{task_id}/comment", response_model=CommentResponse)
async def get_comment(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get comment for an evaluation."""
    logger.debug(f"Fetching comment for task: {task_id}")

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

    # Query evaluation
    eval_result = await db.execute(
        select(Evaluation).where(Evaluation.task_id == task_id)
    )
    evaluation = eval_result.scalar_one_or_none()

    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation for task '{task_id}' not found"
        )

    return CommentResponse(
        code=200,
        message="success",
        data={
            "task_id": str(task_id),
            "evaluation_id": str(evaluation.id),
            "comment": evaluation.comment
        },
        timestamp=datetime.utcnow(),
    )


# @router.get("/latest", response_model=EvaluationResponse)
# async def get_latest_evaluation(
#     style_id: str = Query(..., description="风格ID"),
#     db: AsyncSession = Depends(get_db),
# ):
#     """Get the latest evaluation for a style."""
#     logger.info(f"Fetching latest evaluation for style: {style_id}")

#     # Query the latest evaluation for this style
#     result = await db.execute(
#         select(Evaluation)
#         .where(Evaluation.style_id == style_id)
#         .order_by(Evaluation.created_at.desc())
#     )
#     evaluation = result.scalar_one_or_none()

#     if not evaluation:
#         logger.warning(f"No evaluation found for style: {style_id}")
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"No evaluation found for style '{style_id}'"
#         )

#     logger.info(f"Found evaluation for style {style_id}: overall_score={evaluation.overall_score}")

#     return EvaluationResponse(
#         code=200,
#         message="success",
#         data=evaluation.to_dict(),
#         timestamp=datetime.utcnow(),
#     )
