"""API routes for Style management."""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from ..models import get_db, Style, Task
from ..schemas import (
    Response,
    PaginationParams,
    StyleCreate,
    StyleUpdate,
    StyleResponse,
    StyleListItem,
)
from ..utils import get_logger

router = APIRouter(prefix="/api/styles", tags=["styles"])
logger = get_logger(__name__)


@router.get("", response_model=Response)
async def list_styles(
    search: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """List all styles with pagination and optional search."""
    logger.info(f"Listing styles: page={page}, page_size={page_size}, search={search}")

    # Build query
    query = select(Style)

    if search:
        logger.debug(f"Applying search filter: {search}")
        query = query.where(
            (Style.name.ilike(f"%{search}%")) |
            (Style.description.ilike(f"%{search}%"))
        )

    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()

    # Apply pagination
    query = query.order_by(Style.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    styles = result.scalars().all()

    # Fetch latest task status for each style
    style_items = []
    for style in styles:
        # Get latest task for this style
        task_result = await db.execute(
            select(Task)
            .where(Task.style_id == style.id)
            .order_by(Task.created_at.desc())
            .limit(1)
        )
        latest_task = task_result.scalar_one_or_none()

        # Build item with task_status
        item_data = {
            "id": str(style.id),
            "name": style.name,
            "description": style.description,
            "target_style": style.target_style,
            "status": style.status,
            "task_status": latest_task.status if latest_task else None,
            "created_at": style.created_at,
        }
        style_items.append(StyleListItem.model_validate(item_data))

    # Calculate pagination info
    total_pages = (total + page_size - 1) // page_size

    logger.info(f"Found {total} styles, returning {len(style_items)} items")

    return Response(
        code=200,
        message="success",
        data={
            "items": style_items,
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
async def create_style(
    style_data: StyleCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new style."""
    logger.info(f"Creating style: name={style_data.name}, target_style={style_data.target_style}")

    # Check for duplicate name
    logger.debug(f"Checking for duplicate name: {style_data.name}")
    result = await db.execute(
        select(Style).where(Style.name == style_data.name)
    )
    if result.scalar_one_or_none():
        logger.warning(f"Style with name '{style_data.name}' already exists")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Style with name '{style_data.name}' already exists"
        )

    # Create new style
    new_style = Style(
        name=style_data.name,
        description=style_data.description,
        target_style=style_data.target_style,
        base_model=style_data.base_model,
        status="pending",
    )

    db.add(new_style)
    await db.commit()
    await db.refresh(new_style)

    logger.info(f"Style created successfully: id={new_style.id}")

    return Response(
        code=201,
        message="Style created successfully",
        data=StyleResponse.model_validate(new_style),
        timestamp=datetime.utcnow(),
    )


@router.get("/{style_id}", response_model=Response)
async def get_style(
    style_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific style by ID."""
    logger.debug(f"Fetching style: {style_id}")

    result = await db.execute(
        select(Style).where(Style.id == style_id)
    )
    style = result.scalar_one_or_none()

    if not style:
        logger.warning(f"Style not found: {style_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Style with id '{style_id}' not found"
        )

    logger.debug(f"Found style: {style_id} (name: {style.name}, status: {style.status})")

    return Response(
        code=200,
        message="success",
        data=StyleResponse.model_validate(style),
        timestamp=datetime.utcnow(),
    )


@router.put("/{style_id}", response_model=Response)
async def update_style(
    style_id: str,
    style_data: StyleUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a style."""
    logger.info(f"Updating style: {style_id}")
    logger.debug(f"Update data: {style_data.model_dump(exclude_unset=True)}")

    result = await db.execute(
        select(Style).where(Style.id == style_id)
    )
    style = result.scalar_one_or_none()

    if not style:
        logger.warning(f"Style not found for update: {style_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Style with id '{style_id}' not found"
        )

    # Check for duplicate name if updating name
    if style_data.name and style_data.name != style.name:
        logger.debug(f"Checking for name conflict: {style_data.name}")
        existing = await db.execute(
            select(Style).where(Style.name == style_data.name)
        )
        if existing.scalar_one_or_none():
            logger.warning(f"Name conflict: '{style_data.name}' already exists")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Style with name '{style_data.name}' already exists"
            )

    # Update fields
    update_data = style_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(style, field, value)

    await db.commit()
    await db.refresh(style)

    logger.info(f"Style updated successfully: {style_id}")

    return Response(
        code=200,
        message="Style updated successfully",
        data=StyleResponse.model_validate(style),
        timestamp=datetime.utcnow(),
    )


@router.delete("/{style_id}", response_model=Response)
async def delete_style(
    style_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a style and associated local files."""
    logger.info(f"Deleting style: {style_id}")

    result = await db.execute(
        select(Style).where(Style.id == style_id)
    )
    style = result.scalar_one_or_none()

    if not style:
        logger.warning(f"Style not found for deletion: {style_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Style with id '{style_id}' not found"
        )

    logger.info(f"Style status: {style.status}, name: {style.name}")

    # Check if style is currently training or has active tasks
    from ..models import Task

    # Check for any active tasks (PENDING or PROCESSING)
    active_tasks_result = await db.execute(
        select(Task).where(
            Task.style_id == style_id,
            Task.status.in_(["PENDING", "PROCESSING"])
        )
    )
    active_tasks = active_tasks_result.scalars().all()

    if active_tasks:
        task_statuses = [t.status for t in active_tasks]
        logger.warning(
            f"Cannot delete style {style_id}: has {len(active_tasks)} active tasks "
            f"with statuses: {task_statuses}"
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot delete style with active training tasks. "
                   f"Found {len(active_tasks)} task(s) with status: {', '.join(set(task_statuses))}"
        )

    # Also check style status as a safeguard
    if style.status == "training":
        logger.warning(f"Style {style_id} has 'training' status but no active tasks found")
        # Reset status to allow deletion or block it
        logger.info(f"Resetting style {style_id} status from 'training' to 'pending'")
        style.status = "pending"

    # Collect files to delete before deleting database records
    import os
    import shutil
    files_to_delete = []
    dirs_to_delete = []

    # 1. Adapter path from style
    if style.adapter_path:
        adapter_path = style.adapter_path
        if os.path.exists(adapter_path):
            files_to_delete.append(adapter_path)
            logger.info(f"Will delete adapter: {adapter_path}")

    # 2. Get all tasks for this style to find training data paths
    tasks_result = await db.execute(
        select(Task).where(Task.style_id == style_id)
    )
    tasks = tasks_result.scalars().all()

    for task in tasks:
        # Training data path
        if task.training_data_path and os.path.exists(task.training_data_path):
            dirs_to_delete.append(task.training_data_path)
            logger.info(f"Will delete training data: {task.training_data_path}")

        # Result path (adapter files from tasks)
        if task.result_path and task.result_path != style.adapter_path:
            if os.path.exists(task.result_path):
                files_to_delete.append(task.result_path)
                logger.info(f"Will delete task result: {task.result_path}")

    # Delete the style (cascade will handle related messages and tasks in DB)
    await db.delete(style)
    await db.commit()

    # Delete local files after successful DB deletion
    deleted_files = []
    deleted_dirs = []
    failed_deletions = []

    # Delete files
    for file_path in files_to_delete:
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
                deleted_files.append(file_path)
                logger.info(f"Deleted file: {file_path}")
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
                deleted_files.append(file_path)
                logger.info(f"Deleted directory: {file_path}")
        except Exception as e:
            failed_deletions.append((file_path, str(e)))
            logger.error(f"Failed to delete {file_path}: {e}")

    # Delete directories
    for dir_path in dirs_to_delete:
        try:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
                deleted_dirs.append(dir_path)
                logger.info(f"Deleted directory: {dir_path}")
        except Exception as e:
            failed_deletions.append((dir_path, str(e)))
            logger.error(f"Failed to delete {dir_path}: {e}")

    logger.info(f"Style deleted successfully: {style_id}")
    logger.info(f"Deleted {len(deleted_files)} files/directories, {len(failed_deletions)} failed")

    return Response(
        code=200,
        message="Style deleted successfully",
        data={
            "id": style_id,
            "deleted_files": deleted_files + deleted_dirs,
            "failed_deletions": failed_deletions
        },
        timestamp=datetime.utcnow(),
    )
