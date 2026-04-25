"""API routes for Adapter management."""

import json
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_, and_

from app.models import get_db, Adapter, DownloadLog
from app.schemas import AdapterUpdate, AdapterResponse, AdapterListItem
from app.dependencies import get_current_user, get_current_user_optional
from app.services import file_storage

router = APIRouter(prefix="/adapters", tags=["adapters"])


async def _recalculate_weekly_downloads(db: AsyncSession) -> None:
    """Recalculate weekly download counts for all adapters."""
    one_week_ago = datetime.utcnow() - timedelta(days=7)

    result = await db.execute(
        select(
            DownloadLog.resource_id,
            func.count(DownloadLog.id).label("weekly_count")
        )
        .where(
            and_(
                DownloadLog.resource_type == "adapter",
                DownloadLog.downloaded_at >= one_week_ago
            )
        )
        .group_by(DownloadLog.resource_id)
    )

    weekly_counts = {str(row.resource_id): row.weekly_count for row in result.all()}

    all_adapters = (await db.execute(select(Adapter))).scalars().all()
    for adapter in all_adapters:
        adapter.weekly_download_count = weekly_counts.get(str(adapter.id), 0)

    await db.commit()


def _get_sort_column(sort_by: str):
    """Get SQLAlchemy column for sorting."""
    sort_map = {
        "upload_time": Adapter.upload_time,
        "download_count": Adapter.download_count,
        "weekly_download_count": Adapter.weekly_download_count,
        "style_name": Adapter.style_name,
    }
    return sort_map.get(sort_by, Adapter.upload_time)


@router.get("", response_model=dict)
async def list_adapters(
    search: Optional[str] = Query(None, description="Search keyword"),
    style_tag: Optional[str] = Query(None, description="Filter by tag"),
    base_model: Optional[str] = Query(None, description="Filter by base model"),
    sort_by: str = Query("upload_time", description="Sort field"),
    sort_order: str = Query("desc", description="Sort direction"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    mine: bool = Query(False, description="Only show my uploads"),
    current_user = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """List adapters with search, sort, and pagination."""
    if mine:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to view your uploads"
            )

    await _recalculate_weekly_downloads(db)

    query = select(Adapter).where(Adapter.is_active == True)

    if mine and current_user:
        query = query.where(Adapter.uploader_id == current_user.id)

    if search:
        search_filter = or_(
            Adapter.style_name.ilike(f"%{search}%"),
            Adapter.style_tag.ilike(f"%{search}%"),
            Adapter.description.ilike(f"%{search}%"),
            Adapter.uploader_name.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)

    if style_tag:
        query = query.where(Adapter.style_tag == style_tag)

    if base_model:
        query = query.where(Adapter.base_model == base_model)

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()

    sort_column = _get_sort_column(sort_by)
    if sort_order.lower() == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    adapters = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    items = []
    for a in adapters:
        item = AdapterListItem.model_validate(a)
        if a.evaluation_results and isinstance(a.evaluation_results, dict):
            item.overall_score = a.evaluation_results.get("overall_score")
            item.evaluation_results = a.evaluation_results
        items.append(item)

    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": [item.model_dump() for item in items],
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }
        },
    }


@router.get("/{adapter_id}", response_model=dict)
async def get_adapter(
    adapter_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get adapter details by ID."""
    result = await db.execute(
        select(Adapter).where(Adapter.id == adapter_id, Adapter.is_active == True)
    )
    adapter = result.scalar_one_or_none()

    if not adapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Adapter with id '{adapter_id}' not found"
        )

    return {
        "code": 200,
        "message": "success",
        "data": AdapterResponse.model_validate(adapter).model_dump(),
    }


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_adapter(
    style_name: str = Form(..., min_length=1, max_length=100),
    style_tag: str = Form(..., min_length=1, max_length=50),
    description: Optional[str] = Form(None, max_length=2000),
    base_model: str = Form(..., min_length=1, max_length=50),
    evaluation_results: Optional[str] = Form(None, description="Evaluation results JSON string"),
    local_style_id: Optional[str] = Form(None, description="Local backend style ID (UUID) to prevent duplicate uploads"),
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a new adapter (auth required)."""
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .zip files are allowed for adapter uploads"
        )

    # Check for duplicate uploads from the same local style
    if local_style_id:
        existing = await db.execute(
            select(Adapter).where(
                Adapter.local_style_id == local_style_id,
                Adapter.is_active == True,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This style has already been uploaded to the cloud"
            )

    record_id = uuid.uuid4()

    try:
        file_path, file_size, stored_filename = await file_storage.save_adapter_file(
            file, str(current_user.id), str(record_id)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )

    parsed_evaluation = None
    if evaluation_results:
        try:
            parsed_evaluation = json.loads(evaluation_results)
        except json.JSONDecodeError:
            parsed_evaluation = None

    adapter = Adapter(
        id=record_id,
        style_name=style_name,
        style_tag=style_tag,
        description=description,
        base_model=base_model,
        file_path=file_path,
        file_size=file_size,
        file_name=file.filename,
        local_style_id=local_style_id,
        uploader_id=current_user.id,
        uploader_name=current_user.username,
        upload_time=datetime.utcnow(),
        download_count=0,
        weekly_download_count=0,
        evaluation_results=parsed_evaluation,
        is_active=True,
    )

    db.add(adapter)
    await db.commit()
    await db.refresh(adapter)

    return {
        "code": 201,
        "message": "Adapter uploaded successfully",
        "data": AdapterResponse.model_validate(adapter).model_dump(),
    }


@router.get("/{adapter_id}/download")
async def download_adapter(
    adapter_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Download adapter file. Increments download counters."""
    from fastapi.responses import FileResponse

    result = await db.execute(
        select(Adapter).where(Adapter.id == adapter_id, Adapter.is_active == True)
    )
    adapter = result.scalar_one_or_none()

    if not adapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Adapter with id '{adapter_id}' not found"
        )

    if not file_storage.file_exists(adapter.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Adapter file not found on server"
        )

    adapter.download_count += 1
    adapter.weekly_download_count += 1

    download_log = DownloadLog(
        resource_id=adapter.id,
        resource_type="adapter",
        downloaded_at=datetime.utcnow(),
    )
    db.add(download_log)

    await db.commit()

    return FileResponse(
        path=adapter.file_path,
        filename=adapter.file_name,
        media_type="application/zip",
    )


@router.delete("/{adapter_id}", response_model=dict)
async def delete_adapter(
    adapter_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an adapter (owner only). Removes DB record and local file."""
    result = await db.execute(
        select(Adapter).where(Adapter.id == adapter_id)
    )
    adapter = result.scalar_one_or_none()

    if not adapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Adapter with id '{adapter_id}' not found"
        )

    if str(adapter.uploader_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own adapters"
        )

    file_path = adapter.file_path

    await db.delete(adapter)
    await db.commit()

    if file_path:
        file_storage.delete_file(file_path)

    return {
        "code": 200,
        "message": "Adapter deleted successfully",
        "data": {"id": adapter_id},
    }


@router.put("/{adapter_id}", response_model=dict)
async def update_adapter(
    adapter_id: str,
    update_data: AdapterUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update adapter metadata (owner only)."""
    result = await db.execute(
        select(Adapter).where(Adapter.id == adapter_id, Adapter.is_active == True)
    )
    adapter = result.scalar_one_or_none()

    if not adapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Adapter with id '{adapter_id}' not found"
        )

    if str(adapter.uploader_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own adapters"
        )

    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(adapter, field, value)

    await db.commit()
    await db.refresh(adapter)

    return {
        "code": 200,
        "message": "Adapter updated successfully",
        "data": AdapterResponse.model_validate(adapter).model_dump(),
    }
