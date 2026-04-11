"""API routes for Task management."""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from ..models import get_db, Task, Style
from ..schemas import (
    Response,
    TaskCreate,
    TaskResponse,
    TaskListItem,
    TaskLogsResponse,
)
from ..celery_app import train_style_model
from ..utils import get_logger

router = APIRouter(prefix="/api/tasks", tags=["tasks"])
logger = get_logger(__name__)


@router.get("", response_model=Response)
async def list_tasks(
    style_id: Optional[str] = Query(None, description="按风格ID筛选"),
    status: Optional[str] = Query(None, description="按状态筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """List all training tasks with pagination and filtering."""
    logger.info(f"Listing tasks: page={page}, page_size={page_size}, style_id={style_id}, status={status}")

    query = select(Task)

    if style_id:
        query = query.where(Task.style_id == style_id)
    if status:
        query = query.where(Task.status == status)

    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()

    # Apply pagination
    query = query.order_by(Task.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    tasks = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    logger.info(f"Found {total} tasks, returning {len(tasks)} items")

    return Response(
        code=200,
        message="success",
        data={
            "items": [TaskListItem.model_validate(t) for t in tasks],
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }
        },
        timestamp=datetime.utcnow(),
    )


@router.post("", response_model=Response, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new training task."""
    logger.info(f"Creating training task for style_id={task_data.style_id}")
    logger.debug(f"Task config: {task_data.config}")

    # Verify style exists
    logger.debug(f"Looking up style: {task_data.style_id}")
    result = await db.execute(
        select(Style).where(Style.id == task_data.style_id)
    )
    style = result.scalar_one_or_none()

    if not style:
        logger.warning(f"Style not found: {task_data.style_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Style with id '{task_data.style_id}' not found"
        )

    logger.info(f"Found style: {style.name} (status: {style.status})")

    # Check if style is already training
    if style.status == "training":
        logger.warning(f"Style {task_data.style_id} is already being trained")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Style is already being trained"
        )

    # Update style status
    style.status = "training"
    style.base_model = task_data.base_model
    logger.info(f"Updated style status to 'training'")

    # Create task
    config_dict = task_data.config.model_dump() if task_data.config else {}

    new_task = Task(
        style_id=task_data.style_id,
        status="PENDING",
        progress=0,
        config=config_dict,
        current_epoch=0,
        total_epochs=config_dict.get("num_epochs", 3),
    )

    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    logger.info(f"Created task with ID: {new_task.id}")
    logger.info(f"Training text length: {len(task_data.training_text)} chars")

    # Start Celery task
    logger.info(f"Starting Celery task for task_id={new_task.id}")
    try:
        import time
        celery_start = time.time()

        # Check if Celery is available
        from ..celery_app.tasks import celery_app
        inspect = celery_app.control.inspect()
        workers = inspect.ping()
        if not workers:
            logger.warning("No Celery workers detected! Task will be queued but may not process.")
        else:
            logger.info(f"Celery workers available: {list(workers.keys())}")

        celery_job = train_style_model.delay(
            task_id=str(new_task.id),
            style_id=task_data.style_id,
            training_text=task_data.training_text,
            config=config_dict,
        )
        celery_elapsed = time.time() - celery_start
        logger.info(f"Celery task started successfully: job_id={celery_job.id} in {celery_elapsed:.3f}s")

        if celery_elapsed > 5:
            logger.warning(f"Celery task dispatch took {celery_elapsed:.1f}s - this may indicate a problem")

    except Exception as e:
        logger.error(f"Failed to start Celery task: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start training task: {str(e)}"
        )

    return Response(
        code=201,
        message="Training task created successfully",
        data=TaskResponse.model_validate(new_task),
        timestamp=datetime.utcnow(),
    )


@router.get("/{task_id}", response_model=Response)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific task by ID."""
    logger.debug(f"Fetching task: {task_id}")

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

    logger.debug(f"Found task: {task_id} (status: {task.status}, progress: {task.progress}%)")

    return Response(
        code=200,
        message="success",
        data=TaskResponse.model_validate(task),
        timestamp=datetime.utcnow(),
    )


@router.get("/{task_id}/logs", response_model=Response)
async def get_task_logs(
    task_id: str,
    lines: int = Query(50, ge=1, le=500, description="返回的日志行数"),
    db: AsyncSession = Depends(get_db),
):
    """Get training logs for a task."""
    logger.debug(f"Fetching logs for task: {task_id}, lines={lines}")

    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        logger.warning(f"Task not found for logs: {task_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id '{task_id}' not found"
        )

    # Get last N lines of logs
    log_content = task.logs or ""
    log_lines = log_content.split("\n")
    last_lines = log_lines[-lines:] if len(log_lines) > lines else log_lines

    logger.debug(f"Returning {len(last_lines)} log lines (total: {len(log_lines)})")

    return Response(
        code=200,
        message="success",
        data=TaskLogsResponse(
            task_id=task_id,
            logs="\n".join(last_lines),
            lines=len(last_lines),
        ),
        timestamp=datetime.utcnow(),
    )
