"""WebSocket endpoints for real-time training progress."""

import os
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional

import redis.asyncio as redis

from .manager import manager
from ..services import evaluation_service
from ..models import Task, AsyncSessionLocal
from ..utils import get_logger

router = APIRouter()
logger = get_logger(__name__)


async def redis_listener(websocket: WebSocket, task_id: str, stop_event: asyncio.Event):
    """Listen to Redis pub/sub for task progress updates."""
    redis_client = None
    logger.debug(f"Redis listener started for task: {task_id}")

    try:
        redis_client = redis.Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True
        )
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"task:{task_id}")
        logger.info(f"Subscribed to Redis channel: task:{task_id}")

        message_count = 0
        while not stop_event.is_set():
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
            if message:
                message_count += 1
                try:
                    data = json.loads(message["data"])
                    logger.debug(f"Received Redis message #{message_count} for task {task_id}: {data.get('type', 'unknown')}")
                    await websocket.send_json(data)
                    logger.debug(f"Forwarded message to WebSocket client")
                except Exception as e:
                    logger.error(f"Error sending WebSocket message: {e}")
                    break

        logger.debug(f"Redis listener stopped for task {task_id}, processed {message_count} messages")

    except Exception as e:
        logger.error(f"Redis listener error for task {task_id}: {e}", exc_info=True)
    finally:
        if redis_client:
            await redis_client.close()
            logger.debug(f"Redis connection closed for task {task_id}")


@router.websocket("/ws/tasks/{task_id}")
async def task_progress_websocket(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint for real-time training progress updates.

    Args:
        websocket: WebSocket connection
        task_id: Training task ID to monitor
    """
    client_host = websocket.client.host if websocket.client else "unknown"
    logger.info(f"WebSocket connection request from {client_host} for task: {task_id}")

    await manager.connect(websocket, task_id)
    logger.info(f"WebSocket connection established for task: {task_id}")

    # Create stop event for Redis listener
    stop_event = asyncio.Event()

    # Start Redis listener in background
    listener_task = asyncio.create_task(
        redis_listener(websocket, task_id, stop_event)
    )
    logger.debug(f"Redis listener task created for task: {task_id}")

    try:
        # Send current task status on connection
        logger.debug(f"Fetching current status for task: {task_id}")
        async with AsyncSessionLocal() as session:
            from sqlalchemy.future import select
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()

            if task:
                logger.info(f"Sending initial status for task {task_id}: status={task.status}, progress={task.progress}%")
                await manager.send_progress_update(
                    task_id=task_id,
                    status=task.status,
                    progress=task.progress,
                    current_epoch=task.current_epoch,
                    total_epochs=task.total_epochs,
                    current_loss=task.current_loss,
                    elapsed_time=task.elapsed_time,
                    estimated_remaining=task.estimated_remaining,
                    log_lines=task.logs.split("\n")[-10:] if task.logs else [],
                )
            else:
                logger.warning(f"Task not found for WebSocket: {task_id}")
                await manager.send_personal_message({
                    "type": "error",
                    "data": {"message": f"Task {task_id} not found"},
                }, websocket)

        # Keep connection alive and handle ping/pong
        ping_count = 0
        while True:
            try:
                # Wait for messages from client (ping or close)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )

                # Handle ping
                if data == "ping":
                    ping_count += 1
                    logger.debug(f"Received ping #{ping_count} from client for task {task_id}")
                    await websocket.send_text("pong")

            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await websocket.send_text("ping")
                    logger.debug(f"Sent keepalive ping to client for task {task_id}")
                except Exception as e:
                    logger.debug(f"Failed to send keepalive ping for task {task_id}: {e}")
                    break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for task: {task_id}")
    except Exception as e:
        logger.error(f"WebSocket error for task {task_id}: {e}", exc_info=True)
        try:
            await manager.send_personal_message({
                "type": "error",
                "data": {"message": str(e)},
            }, websocket)
        except Exception:
            pass
    finally:
        logger.info(f"Cleaning up WebSocket connection for task: {task_id}")
        # Stop Redis listener
        stop_event.set()
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            logger.debug(f"Redis listener task cancelled for task {task_id}")
        manager.disconnect(websocket)
        logger.info(f"WebSocket connection closed for task: {task_id}")
