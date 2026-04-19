"""API routes for Message/Chat management."""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from ..models import get_db, Message, Style
from ..schemas import (
    Response,
    MessageCreate,
    MessageResponse,
    StyleTransferRequest,
)
from ..services import inference_service
from ..utils import get_logger

router = APIRouter(prefix="/api/styles", tags=["messages"])
logger = get_logger(__name__)


@router.get("/{style_id}/messages", response_model=Response)
async def list_messages(
    style_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """Get chat history for a specific style."""
    logger.info(f"Listing messages for style: {style_id}, page={page}, page_size={page_size}")

    # Verify style exists
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

    # Get messages
    query = select(Message).where(Message.style_id == style_id)

    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()

    # Apply pagination (newest first)
    query = query.order_by(Message.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    messages = result.scalars().all()

    # Reverse for chronological order
    messages = list(reversed(messages))

    total_pages = (total + page_size - 1) // page_size

    logger.info(f"Found {total} messages, returning {len(messages)} items")

    return Response(
        code=200,
        message="success",
        data={
            "items": [MessageResponse.model_validate(m) for m in messages],
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }
        },
        timestamp=datetime.utcnow(),
    )


@router.post("/{style_id}/messages", response_model=Response)
async def create_message(
    style_id: str,
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db),
):
    """Send a style transfer request and get AI response."""
    logger.info(f"Creating message for style: {style_id}")

    # Verify style exists
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

    # Check if style is available for use
    if style.status not in ["available", "completed", "pending"]:
        logger.warning(f"Style not available: {style_id} has status {style.status}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Style is not available for use (status: {style.status})"
        )

    # Call LLM API for style transfer
    try:
        logger.info(f"Calling inference service for style transfer")
        response_text = await inference_service.generate_style_transfer(
            original_text=message_data.original_text,
            requirement=message_data.requirement,
            target_style=style.target_style,
            history=message_data.history,
            style_id=style_id,
        )
        logger.info(f"Inference service returned response ({len(response_text)} chars)")
    except ValueError as e:
        logger.error(f"LLM service not configured: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM service not configured: {str(e)}"
        )
    except RuntimeError as e:
        logger.error(f"Generate response failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Generate response failed: {str(e)}"
        )

    # Save user message
    logger.debug(f"Saving user message")
    user_message = Message(
        style_id=style_id,
        role="user",
        content=message_data.requirement,
        original_text=message_data.original_text,
        requirement=message_data.requirement,
    )
    db.add(user_message)

    # Save assistant response
    logger.debug(f"Saving assistant response")
    assistant_message = Message(
        style_id=style_id,
        role="assistant",
        content=response_text,
        original_text=message_data.original_text,
        requirement=message_data.requirement,
        meta_data={
            "original_text": message_data.original_text,
            "requirement": message_data.requirement,
        }
    )
    db.add(assistant_message)
    await db.commit()
    await db.refresh(assistant_message)

    logger.info(f"Message created successfully")

    return Response(
        code=200,
        message="success",
        data={
            "message": MessageResponse.model_validate(assistant_message),
            "style_name": style.name,
        },
        timestamp=datetime.utcnow(),
    )


@router.delete("/{style_id}/messages", response_model=Response)
async def clear_messages(
    style_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Clear all messages for a style."""
    logger.info(f"Clearing messages for style: {style_id}")

    # Verify style exists
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

    # Delete all messages for this style
    from sqlalchemy import delete
    delete_result = await db.execute(
        delete(Message).where(Message.style_id == style_id)
    )
    await db.commit()

    deleted_count = delete_result.rowcount
    logger.info(f"Cleared {deleted_count} messages for style: {style_id}")

    return Response(
        code=200,
        message="Messages cleared successfully",
        data={"style_id": style_id, "deleted_count": deleted_count},
        timestamp=datetime.utcnow(),
    )


@router.delete("/{style_id}/messages/{message_id}", response_model=Response)
async def delete_message(
    style_id: str,
    message_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single message."""
    logger.info(f"Deleting message: {message_id} for style: {style_id}")

    # Verify style exists
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

    # Find the message
    result = await db.execute(
        select(Message).where(Message.id == message_id, Message.style_id == style_id)
    )
    message = result.scalar_one_or_none()

    if not message:
        logger.warning(f"Message not found: {message_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message with id '{message_id}' not found"
        )

    # Delete the message
    await db.delete(message)
    await db.commit()

    logger.info(f"Message {message_id} deleted successfully")

    return Response(
        code=200,
        message="Message deleted successfully",
        data={"style_id": style_id, "message_id": message_id},
        timestamp=datetime.utcnow(),
    )
