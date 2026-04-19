"""API routes for Style management."""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, update

from ..models import get_db, Style, Task
from ..schemas import (
    Response,
    PaginationParams,
    StyleCreate,
    StyleUpdate,
    StyleResponse,
    StyleListItem,
    BaseModelInfo,
)
from ..utils import get_logger, get_available_models

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

    # 同步更新关联 tasks 的 name 字段
    if "name" in update_data:
        await db.execute(
            update(Task)
            .where(Task.style_id == style_id)
            .values(name=update_data["name"])
        )
        logger.info(f"同步更新 tasks 名称: style_id={style_id}, name={update_data['name']}")

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
    logger.info(f"Deleting style: {style_id}")

    import os
    import shutil
    from ..models import Task

    # ---- 1. 获取 style ----
    style = await db.scalar(
        select(Style).where(Style.id == style_id)
    )

    if not style:
        raise HTTPException(
            status_code=404,
            detail=f"Style '{style_id}' not found"
        )

    # ---- 2. 检查 active tasks（只查 count，避免加载全部对象）----
    active_count = await db.scalar(
        select(func.count())
        .select_from(Task)
        .where(
            Task.style_id == style_id,
            Task.status.in_(["PENDING", "PROCESSING"])
        )
    )

    if active_count > 0:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot delete style: {active_count} active tasks exist"
        )

    # ---- 3. 获取所有 tasks（一次查询）----
    tasks = (await db.scalars(
        select(Task).where(Task.style_id == style_id)
    )).all()

    # ---- 4. 收集需要删除的路径（用 set 去重）----
    file_paths: set[str] = set()
    dir_paths: set[str] = set()

    if style.adapter_path:
        file_paths.add(style.adapter_path)

    for task in tasks:
        if task.training_data_path:
            dir_paths.add(task.training_data_path)

    # ---- 5. 先删除 DB（事务保证一致性）----
    await db.delete(style)
    await db.commit()

    # ---- 6. 删除文件（DB 成功后执行）----
    deleted = []
    failed = []

    def safe_delete(path: str):
        try:
            if os.path.isfile(path):
                os.remove(path)
                return True
            elif os.path.isdir(path):
                shutil.rmtree(path)
                return True
        except Exception as e:
            logger.error(f"Delete failed: {path}, error: {e}")
            failed.append({"path": path, "error": str(e)})
        return False

    for path in file_paths | dir_paths:
        if os.path.exists(path):
            if safe_delete(path):
                deleted.append(path)

    logger.info(
        f"Style {style_id} deleted. files={len(deleted)}, failed={len(failed)}"
    )

    return Response(
        code=200,
        message="Style deleted successfully",
        data={
            "id": style_id,
            "deleted_files": deleted,
            "failed_deletions": failed
        },
        timestamp=datetime.utcnow(),
    )


# ---- Models router (separate prefix) ----
models_router = APIRouter(prefix="/api/models", tags=["models"])


@models_router.get("", response_model=Response)
async def list_base_models():
    """List all available base models from YAML config."""
    models = get_available_models()
    return Response(
        code=200,
        message="success",
        data=[BaseModelInfo.model_validate(m) for m in models],
        timestamp=datetime.utcnow(),
    )