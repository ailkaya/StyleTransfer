"""WebSocket connection manager for training progress."""

import json
from typing import Dict, Set
from datetime import datetime
from fastapi import WebSocket

from ..utils import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for task progress updates."""

    def __init__(self):
        # Map task_id to set of WebSocket connections
        self.task_connections: Dict[str, Set[WebSocket]] = {}
        # Map websocket to task_id for cleanup
        self.websocket_tasks: Dict[WebSocket, str] = {}
        logger.info("WebSocket ConnectionManager initialized")

    async def connect(self, websocket: WebSocket, task_id: str):
        """Accept WebSocket connection and register it."""
        client_host = websocket.client.host if websocket.client else "unknown"
        logger.info(f"Accepting WebSocket connection for task {task_id} from {client_host}")

        await websocket.accept()

        if task_id not in self.task_connections:
            self.task_connections[task_id] = set()
            logger.debug(f"Created new connection set for task {task_id}")

        self.task_connections[task_id].add(websocket)
        self.websocket_tasks[websocket] = task_id

        connection_count = len(self.task_connections[task_id])
        logger.info(f"WebSocket connected for task {task_id}. Total connections: {connection_count}")

        # Send connection confirmation
        await self.send_personal_message({
            "type": "connected",
            "data": {"task_id": task_id, "message": "WebSocket connected"},
            "timestamp": datetime.utcnow().isoformat(),
        }, websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        task_id = self.websocket_tasks.pop(websocket, None)
        if task_id and task_id in self.task_connections:
            self.task_connections[task_id].discard(websocket)
            remaining = len(self.task_connections[task_id])
            logger.info(f"WebSocket disconnected from task {task_id}. Remaining connections: {remaining}")
            if not self.task_connections[task_id]:
                del self.task_connections[task_id]
                logger.debug(f"Removed empty connection set for task {task_id}")
        else:
            logger.debug("Disconnected WebSocket was not registered")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to a specific WebSocket."""
        try:
            await websocket.send_json(message)
            logger.debug(f"Sent personal message: {message.get('type')}")
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            # Connection might be closed
            self.disconnect(websocket)

    async def broadcast_to_task(self, task_id: str, message: dict):
        """Broadcast message to all connections watching a task."""
        if task_id not in self.task_connections:
            logger.debug(f"No WebSocket connections for task {task_id}")
            return

        connections = self.task_connections[task_id]
        logger.debug(f"Broadcasting to {len(connections)} connections for task {task_id}")

        disconnected = []
        success_count = 0
        for connection in connections:
            try:
                await connection.send_json(message)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to broadcast message: {e}")
                disconnected.append(connection)

        # Clean up disconnected websockets
        for conn in disconnected:
            self.disconnect(conn)

        logger.debug(f"Broadcast complete: {success_count}/{len(connections)} messages sent")

    async def send_progress_update(
        self,
        task_id: str,
        status: str,
        progress: int,
        current_epoch: int = None,
        total_epochs: int = None,
        current_loss: float = None,
        elapsed_time: int = None,
        estimated_remaining: int = None,
        log_lines: list = None,
    ):
        """Send progress update to all connections watching a task."""
        message = {
            "type": "progress",
            "data": {
                "task_id": task_id,
                "status": status,
                "progress": progress,
                "current_epoch": current_epoch,
                "total_epochs": total_epochs,
                "current_loss": current_loss,
                "elapsed_time": elapsed_time,
                "estimated_remaining": estimated_remaining,
                "log_lines": log_lines or [],
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
        logger.debug(
            f"Sending progress update for task {task_id}: "
            f"status={status}, progress={progress}%"
        )
        await self.broadcast_to_task(task_id, message)

    async def send_completion_notification(self, task_id: str, success: bool = True):
        """Send task completion notification."""
        message = {
            "type": "completed" if success else "failed",
            "data": {
                "task_id": task_id,
                "status": "COMPLETED" if success else "FAILED",
                "progress": 100 if success else 0,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
        logger.info(f"Sending completion notification for task {task_id}: success={success}")
        await self.broadcast_to_task(task_id, message)


# Global connection manager instance
manager = ConnectionManager()
