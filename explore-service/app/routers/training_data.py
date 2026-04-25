"""API routes for TrainingData management."""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_, and_

from app.models import get_db, TrainingData, DownloadLog
from app.schemas import TrainingDataUpdate, TrainingDataResponse, TrainingDataListItem, TrainingDataPreviewResponse
from app.dependencies import get_current_user, get_current_user_optional
from app.services import file_storage

router = APIRouter(prefix="/training-data", tags=["training-data"])


def _get_sort_column(sort_by: str):
    """Get SQLAlchemy column for sorting."""
    sort_map = {
        "upload_time": TrainingData.upload_time,
        "download_count": TrainingData.download_count,
        "title": TrainingData.title,
    }
    return sort_map.get(sort_by, TrainingData.upload_time)


@router.get("", response_model=dict)
async def list_training_data(
    search: Optional[str] = Query(None, description="Search keyword"),
    sort_by: str = Query("upload_time", description="Sort field"),
    sort_order: str = Query("desc", description="Sort direction"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    mine: bool = Query(False, description="Only show my uploads"),
    current_user = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """List training data with search, sort, and pagination."""
    if mine:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to view your uploads"
            )

    query = select(TrainingData).where(TrainingData.is_active == True)

    if mine and current_user:
        query = query.where(TrainingData.uploader_id == current_user.id)

    if search:
        search_filter = or_(
            TrainingData.title.ilike(f"%{search}%"),
            TrainingData.description.ilike(f"%{search}%"),
            TrainingData.uploader_name.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)

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
    items = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": [TrainingDataListItem.model_validate(i).model_dump() for i in items],
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }
        },
    }


@router.get("/{data_id}", response_model=dict)
async def get_training_data(
    data_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get training data details by ID."""
    result = await db.execute(
        select(TrainingData).where(TrainingData.id == data_id, TrainingData.is_active == True)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training data with id '{data_id}' not found"
        )

    return {
        "code": 200,
        "message": "success",
        "data": TrainingDataResponse.model_validate(item).model_dump(),
    }


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_training_data(
    title: str = Form(..., min_length=1, max_length=100),
    description: Optional[str] = Form(None, max_length=2000),
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload new training data (auth required)."""
    allowed_extensions = {".txt", ".csv", ".json", ".jsonl"}
    ext = "." + (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Allowed file types: {', '.join(allowed_extensions)}"
        )

    record_id = uuid.uuid4()

    try:
        file_path, file_size, stored_filename = await file_storage.save_training_data_file(
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

    training_data = TrainingData(
        id=record_id,
        title=title,
        description=description,
        file_path=file_path,
        file_size=file_size,
        file_name=file.filename,
        uploader_id=current_user.id,
        uploader_name=current_user.username,
        upload_time=datetime.utcnow(),
        download_count=0,
        is_active=True,
    )

    db.add(training_data)
    await db.commit()
    await db.refresh(training_data)

    return {
        "code": 201,
        "message": "Training data uploaded successfully",
        "data": TrainingDataResponse.model_validate(training_data).model_dump(),
    }


@router.get("/{data_id}/download")
async def download_training_data(
    data_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Download training data file."""
    from fastapi.responses import FileResponse

    result = await db.execute(
        select(TrainingData).where(TrainingData.id == data_id, TrainingData.is_active == True)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training data with id '{data_id}' not found"
        )

    if not file_storage.file_exists(item.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training data file not found on server"
        )

    item.download_count += 1

    download_log = DownloadLog(
        resource_id=item.id,
        resource_type="training_data",
        downloaded_at=datetime.utcnow(),
    )
    db.add(download_log)

    await db.commit()

    media_type = "text/plain"
    if item.file_name.endswith(".csv"):
        media_type = "text/csv"
    elif item.file_name.endswith(".json"):
        media_type = "application/json"

    return FileResponse(
        path=item.file_path,
        filename=item.file_name,
        media_type=media_type,
    )


@router.get("/{data_id}/preview", response_model=dict)
async def preview_training_data(
    data_id: str,
    line_count: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Preview first N lines of training data file."""
    result = await db.execute(
        select(TrainingData).where(TrainingData.id == data_id, TrainingData.is_active == True)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training data with id '{data_id}' not found"
        )

    if not file_storage.file_exists(item.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training data file not found on server"
        )

    try:
        preview_lines = []
        total_lines = 0

        with open(item.file_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                total_lines += 1
                if i < line_count:
                    preview_lines.append(line.rstrip("\n"))

        return {
            "code": 200,
            "message": "success",
            "data": TrainingDataPreviewResponse(
                id=str(item.id),
                title=item.title,
                total_lines=total_lines,
                preview_lines=preview_lines,
                has_more=total_lines > line_count,
            ).model_dump(),
        }
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is not a valid text file"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read file: {str(e)}"
        )


@router.delete("/{data_id}", response_model=dict)
async def delete_training_data(
    data_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete training data (owner only)."""
    result = await db.execute(
        select(TrainingData).where(TrainingData.id == data_id)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training data with id '{data_id}' not found"
        )

    if str(item.uploader_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own training data"
        )

    item.is_active = False
    await db.commit()

    return {
        "code": 200,
        "message": "Training data deleted successfully",
        "data": {"id": data_id},
    }


@router.put("/{data_id}", response_model=dict)
async def update_training_data(
    data_id: str,
    update_data: TrainingDataUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update training data metadata (owner only)."""
    result = await db.execute(
        select(TrainingData).where(TrainingData.id == data_id, TrainingData.is_active == True)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training data with id '{data_id}' not found"
        )

    if str(item.uploader_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own training data"
        )

    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item)

    return {
        "code": 200,
        "message": "Training data updated successfully",
        "data": TrainingDataResponse.model_validate(item).model_dump(),
    }
