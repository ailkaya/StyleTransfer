"""Database operations module.

This module provides centralized database operations through the DatabaseOperations class.
It supports both synchronous (Celery) and asynchronous (FastAPI) modes.
"""

import json
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    Task, Style, Evaluation, Message,
    AsyncSessionLocal, get_db
)
from .utils import get_logger

logger = get_logger(__name__)

# Sync database setup for Celery
SYNC_DATABASE_URL = os.getenv(
    "SYNC_DATABASE_URL",
    "postgresql://postgres:postgres@127.0.0.1:5432/style_transfer"
)

_sync_engine = None
_SyncSessionLocal = None


def get_sync_engine():
    """Get or create sync database engine."""
    global _sync_engine
    if _sync_engine is None:
        logger.debug("Creating sync database engine...")
        _sync_engine = create_engine(SYNC_DATABASE_URL)
        logger.debug("Sync database engine created")
    return _sync_engine


def get_sync_session():
    """Get sync database session."""
    global _SyncSessionLocal
    if _SyncSessionLocal is None:
        logger.debug("Creating sync session factory...")
        _SyncSessionLocal = sessionmaker(bind=get_sync_engine())
        logger.debug("Sync session factory created")
    return _SyncSessionLocal()


class DatabaseSession:
    """Base database session context manager.

    Supports both sync and async modes. Can be used as a context manager
    or manually managed.

    Examples:
        # Sync mode (Celery)
        with DatabaseSession() as session:
            task = session.get(Task, task_id)

        # Async mode (FastAPI)
        async with DatabaseSession(async_mode=True) as session:
            task = await session.get(Task, task_id)
    """

    def __init__(self, async_mode: bool = False):
        self.async_mode = async_mode
        self.session: Union[Session, AsyncSession, None] = None
        self._owns_session = False

    def __enter__(self) -> Session:
        """Enter sync context."""
        if self.async_mode:
            raise RuntimeError("Use 'async with' for async mode")
        self.session = get_sync_session()
        self._owns_session = True
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit sync context."""
        if self._owns_session and self.session:
            if exc_type:
                self.session.rollback()
            self.session.close()
            self.session = None
        return False

    async def __aenter__(self) -> AsyncSession:
        """Enter async context."""
        if not self.async_mode:
            raise RuntimeError("Use 'with' for sync mode")
        self.session = AsyncSessionLocal()
        self._owns_session = True
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        if self._owns_session and self.session:
            if exc_type:
                await self.session.rollback()
            await self.session.close()
            self.session = None
        return False

    def get(self) -> Union[Session, AsyncSession]:
        """Get current session, creating one if needed."""
        if self.session is None:
            if self.async_mode:
                self.session = AsyncSessionLocal()
            else:
                self.session = get_sync_session()
            self._owns_session = True
        return self.session

    def commit(self):
        """Commit current transaction."""
        if self.session:
            self.session.commit()

    async def commit_async(self):
        """Commit current transaction (async)."""
        if self.session:
            await self.session.commit()

    def rollback(self):
        """Rollback current transaction."""
        if self.session:
            self.session.rollback()

    async def rollback_async(self):
        """Rollback current transaction (async)."""
        if self.session:
            await self.session.rollback()

    def close(self):
        """Close session if we own it."""
        if self._owns_session and self.session:
            self.session.close()
            self.session = None

    async def close_async(self):
        """Close session if we own it (async)."""
        if self._owns_session and self.session:
            await self.session.close()
            self.session = None


class DatabaseOperations:
    """Centralized database operations class.

    Encapsulates all database operations for Task, Style, Evaluation, and Message models.
    Supports both sync (Celery) and async (FastAPI) modes.

    Examples:
        # Sync usage
        db = DatabaseOperations()
        task = db.get_task(task_id)
        db.update_task_status(task_id, "COMPLETED")

        # Async usage
        db = DatabaseOperations(async_mode=True)
        task = await db.get_task(task_id)
        await db.update_task_status(task_id, "COMPLETED")

        # Shared session for atomic operations
        with DatabaseOperations.shared_session() as db:
            db.update_task_status(task_id, "COMPLETED")
            db.update_style_status(style_id, "available")
            db.commit()
    """

    def __init__(self, async_mode: bool = False, session: Optional[Union[Session, AsyncSession]] = None):
        self.async_mode = async_mode
        self._session = session
        self._owns_session = session is None

    @property
    def session(self) -> Union[Session, AsyncSession]:
        """Get current session."""
        if self._session is None:
            if self.async_mode:
                self._session = AsyncSessionLocal()
            else:
                self._session = get_sync_session()
            self._owns_session = True
        return self._session

    @contextmanager
    @staticmethod
    def shared_session(async_mode: bool = False):
        """Create a shared session context for atomic operations.

        Example:
            with DatabaseOperations.shared_session() as db:
                db.update_task_status(task_id, "COMPLETED")
                db.update_style_status(style_id, "available")
                db.commit()
        """
        db = DatabaseOperations(async_mode=async_mode)
        try:
            yield db
        finally:
            db.close()

    def commit(self):
        """Commit current transaction."""
        if self._owns_session and self._session:
            self._session.commit()

    async def commit_async(self):
        """Commit current transaction (async)."""
        if self._owns_session and self._session:
            await self._session.commit()

    def rollback(self):
        """Rollback current transaction."""
        if self._owns_session and self._session:
            self._session.rollback()

    async def rollback_async(self):
        """Rollback current transaction (async)."""
        if self._owns_session and self._session:
            await self._session.rollback()

    def close(self):
        """Close session if we own it."""
        if self._owns_session and self._session:
            self._session.close()
            self._session = None

    async def close_async(self):
        """Close session if we own it (async)."""
        if self._owns_session and self._session:
            await self._session.close()
            self._session = None

    # ==================== Task Operations ====================

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        stmt = select(Task).where(Task.id == task_id)
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()

    def task_exists(self, task_id: str) -> bool:
        """Check if a task exists by ID."""
        stmt = select(func.count()).select_from(Task).where(Task.id == task_id)
        result = self.session.execute(stmt)
        return result.scalar() > 0

    async def task_exists_async(self, task_id: str) -> bool:
        """Check if a task exists by ID (async)."""
        stmt = select(func.count()).select_from(Task).where(Task.id == task_id)
        result = await self.session.execute(stmt)
        return result.scalar() > 0

    async def get_task_async(self, task_id: str) -> Optional[Task]:
        """Get task by ID (async)."""
        stmt = select(Task).where(Task.id == task_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def get_task_by_style(self, style_id: str, status: Optional[str] = None) -> List[Task]:
        """Get tasks by style ID, optionally filtered by status."""
        stmt = select(Task).where(Task.style_id == style_id)
        if status:
            stmt = stmt.where(Task.status == status)
        result = self.session.execute(stmt)
        return result.scalars().all()

    async def get_task_by_style_async(self, style_id: str, status: Optional[str] = None) -> List[Task]:
        """Get tasks by style ID, optionally filtered by status (async)."""
        stmt = select(Task).where(Task.style_id == style_id)
        if status:
            stmt = stmt.where(Task.status == status)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    def get_latest_task_by_style(self, style_id: str) -> Optional[Task]:
        """Get the most recent task for a style."""
        stmt = select(Task).where(Task.style_id == style_id).order_by(Task.created_at.desc()).limit(1)
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_task_by_style_async(self, style_id: str, status: str = None) -> Optional[Task]:
        """Get the most recent task for a style (async)."""
        stmt = select(Task).where(Task.style_id == style_id)
        if status:
            stmt = stmt.where(Task.status == status)
        stmt = stmt.order_by(Task.created_at.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def update_task_status(self, task_id: str, status: str) -> bool:
        """Update task status."""
        try:
            task = self.get_task(task_id)
            if task:
                old_status = task.status
                task.status = status
                task.error_message = None
                if self._owns_session:
                    self.session.commit()
                logger.info(f"Task {task_id} status updated: {old_status} -> {status}")
                return True
            else:
                logger.warning(f"Task {task_id} not found for status update")
                return False
        except Exception as e:
            logger.error(f"Failed to update task {task_id} status: {e}")
            if self._owns_session:
                self.session.rollback()
            return False

    async def update_task_status_async(self, task_id: str, status: str) -> bool:
        """Update task status (async)."""
        try:
            task = await self.get_task_async(task_id)
            if task:
                old_status = task.status
                task.status = status
                if self._owns_session:
                    await self.session.commit()
                logger.info(f"Task {task_id} status updated: {old_status} -> {status}")
                return True
            else:
                logger.warning(f"Task {task_id} not found for status update")
                return False
        except Exception as e:
            logger.error(f"Failed to update task {task_id} status: {e}")
            if self._owns_session:
                await self.session.rollback()
            return False

    def update_task_progress(self, task_id: str, progress_data: Dict[str, Any]) -> bool:
        """Update task progress."""
        try:
            task = self.get_task(task_id)
            if not task:
                logger.warning(f"Task {task_id} not found for progress update")
                return False

            old_status = task.status
            old_progress = task.progress

            task.status = progress_data.get("status", task.status)
            task.progress = progress_data.get("progress", task.progress)
            task.current_epoch = progress_data.get("current_epoch", task.current_epoch)
            task.current_loss = progress_data.get("current_loss", task.current_loss)
            task.elapsed_time = progress_data.get("elapsed_time", task.elapsed_time)
            task.estimated_remaining = progress_data.get("estimated_remaining", task.estimated_remaining)

            if progress_data.get("status") in ["COMPLETED", "FAILED"]:
                task.completed_at = datetime.utcnow()

            if self._owns_session:
                self.session.commit()

            logger.debug(f"Task {task_id} updated: {old_status}({old_progress}%) -> {task.status}({task.progress}%)")
            return True
        except Exception as e:
            logger.error(f"Failed to update task {task_id} progress: {e}")
            if self._owns_session:
                self.session.rollback()
            return False

    async def update_task_progress_async(self, task_id: str, progress_data: Dict[str, Any]) -> bool:
        """Update task progress (async)."""
        try:
            task = await self.get_task_async(task_id)
            if not task:
                logger.warning(f"Task {task_id} not found for progress update")
                return False

            old_status = task.status
            old_progress = task.progress

            task.status = progress_data.get("status", task.status)
            task.progress = progress_data.get("progress", task.progress)
            task.current_epoch = progress_data.get("current_epoch", task.current_epoch)
            task.current_loss = progress_data.get("current_loss", task.current_loss)
            task.elapsed_time = progress_data.get("elapsed_time", task.elapsed_time)
            task.estimated_remaining = progress_data.get("estimated_remaining", task.estimated_remaining)

            if progress_data.get("status") in ["COMPLETED", "FAILED"]:
                task.completed_at = datetime.utcnow()

            if self._owns_session:
                await self.session.commit()

            logger.debug(f"Task {task_id} updated: {old_status}({old_progress}%) -> {task.status}({task.progress}%)")
            return True
        except Exception as e:
            logger.error(f"Failed to update task {task_id} progress: {e}")
            if self._owns_session:
                await self.session.rollback()
            return False

    def update_task_result(self, task_id: str, error: Optional[str] = None) -> bool:
        """Update task result after completion."""
        try:
            task = self.get_task(task_id)
            if not task:
                logger.error(f"Task {task_id} not found when updating result")
                return False

            if error:
                task.error_message = error
                task.status = "FAILED"

            task.completed_at = datetime.utcnow()

            if self._owns_session:
                self.session.commit()

            logger.info(f"Task {task_id} completed with status: {task.status}")
            return True
        except Exception as e:
            logger.error(f"Failed to update task {task_id} result: {e}")
            if self._owns_session:
                self.session.rollback()
            return False

    async def update_task_result_async(self, task_id: str, error: Optional[str] = None) -> bool:
        """Update task result after completion (async)."""
        try:
            task = await self.get_task_async(task_id)
            if not task:
                logger.error(f"Task {task_id} not found when updating result")
                return False

            if error:
                task.error_message = error
                task.status = "FAILED"

            task.completed_at = datetime.utcnow()

            if self._owns_session:
                await self.session.commit()

            logger.info(f"Task {task_id} completed with status: {task.status}")
            return True
        except Exception as e:
            logger.error(f"Failed to update task {task_id} result: {e}")
            if self._owns_session:
                await self.session.rollback()
            return False

    def update_task_training_data_path(self, task_id: str, training_data_path: str) -> bool:
        """Update task training data path."""
        try:
            task = self.get_task(task_id)
            if task:
                task.training_data_path = training_data_path
                if self._owns_session:
                    self.session.commit()
                logger.info(f"Task {task_id} training_data_path updated: {training_data_path}")
                return True
            else:
                logger.warning(f"Task {task_id} not found")
                return False
        except Exception as e:
            logger.error(f"Failed to update task {task_id} training_data_path: {e}")
            if self._owns_session:
                self.session.rollback()
            return False

    def update_task_training_text_path(self, task_id: str, training_text_path: str) -> bool:
        """Update task raw training text file path."""
        try:
            task = self.get_task(task_id)
            if task:
                task.training_text_path = training_text_path
                if self._owns_session:
                    self.session.commit()
                logger.info(f"Task {task_id} training_text_path updated: {training_text_path}")
                return True
            else:
                logger.warning(f"Task {task_id} not found")
                return False
        except Exception as e:
            logger.error(f"Failed to update task {task_id} training_text_path: {e}")
            if self._owns_session:
                self.session.rollback()
            return False

    def update_task_parent_style_id(self, task_id: str, parent_style_id: Optional[str]) -> bool:
        """Update task parent_style_id."""
        try:
            task = self.get_task(task_id)
            if task:
                task.parent_style_id = parent_style_id
                if self._owns_session:
                    self.session.commit()
                logger.info(f"Task {task_id} parent_style_id updated: {parent_style_id}")
                return True
            else:
                logger.warning(f"Task {task_id} not found")
                return False
        except Exception as e:
            logger.error(f"Failed to update task {task_id} parent_style_id: {e}")
            if self._owns_session:
                self.session.rollback()
            return False

    def get_non_terminal_tasks(self) -> List[Task]:
        """Get all tasks that are not in a terminal state (COMPLETED or FAILED)."""
        stmt = select(Task).where(Task.status.notin_(["COMPLETED", "FAILED"]))
        result = self.session.execute(stmt)
        return result.scalars().all()

    def get_task_count(self, style_id: Optional[str] = None, status: Optional[str] = None) -> int:
        """Count tasks, optionally filtered by style and/or status."""
        stmt = select(func.count()).select_from(Task)
        if style_id:
            stmt = stmt.where(Task.style_id == style_id)
        if status:
            stmt = stmt.where(Task.status == status)
        result = self.session.execute(stmt)
        return result.scalar()

    async def get_task_count_async(self, style_id: Optional[str] = None,
                                   status: Optional[str] = None) -> int:
        """Count tasks, optionally filtered by style and/or status (async)."""
        stmt = select(func.count()).select_from(Task)
        if style_id:
            stmt = stmt.where(Task.style_id == style_id)
        if status:
            stmt = stmt.where(Task.status == status)
        result = await self.session.execute(stmt)
        return result.scalar()

    # ==================== Style Operations ====================

    def get_style(self, style_id: str) -> Optional[Style]:
        """Get style by ID."""
        stmt = select(Style).where(Style.id == style_id)
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_style_async(self, style_id: str) -> Optional[Style]:
        """Get style by ID (async)."""
        stmt = select(Style).where(Style.id == style_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def get_style_by_name(self, name: str) -> Optional[Style]:
        """Get style by name."""
        stmt = select(Style).where(Style.name == name)
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_style_by_name_async(self, name: str) -> Optional[Style]:
        """Get style by name (async)."""
        stmt = select(Style).where(Style.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def list_styles(self, search: Optional[str] = None, page: int = 1,
                   page_size: int = 10) -> tuple[List[Style], int]:
        """List styles with pagination and optional search.

        Returns:
            Tuple of (styles list, total count)
        """
        stmt = select(Style)

        if search:
            stmt = stmt.where(
                (Style.name.ilike(f"%{search}%")) |
                (Style.description.ilike(f"%{search}%"))
            )

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.session.execute(count_stmt).scalar()

        # Apply pagination
        stmt = stmt.order_by(Style.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = self.session.execute(stmt)
        styles = result.scalars().all()

        return styles, total

    async def list_styles_async(self, search: Optional[str] = None, page: int = 1,
                                page_size: int = 10) -> tuple[List[Style], int]:
        """List styles with pagination and optional search (async)."""
        stmt = select(Style)

        if search:
            stmt = stmt.where(
                (Style.name.ilike(f"%{search}%")) |
                (Style.description.ilike(f"%{search}%"))
            )

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar()

        # Apply pagination
        stmt = stmt.order_by(Style.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(stmt)
        styles = result.scalars().all()

        return styles, total

    def update_style_status(self, style_id: str, status: str,
                           adapter_path: Optional[str] = None) -> bool:
        """Update style status."""
        try:
            style = self.get_style(style_id)
            if style:
                old_status = style.status
                style.status = status
                if adapter_path is not None:
                    style.adapter_path = adapter_path
                if self._owns_session:
                    self.session.commit()
                logger.info(f"Style {style_id} status updated: {old_status} -> {status}")
                return True
            else:
                logger.warning(f"Style {style_id} not found for status update")
                return False
        except Exception as e:
            logger.error(f"Failed to update style {style_id} status: {e}")
            if self._owns_session:
                self.session.rollback()
            return False

    async def update_style_status_async(self, style_id: str, status: str,
                                        adapter_path: Optional[str] = None) -> bool:
        """Update style status (async)."""
        try:
            style = await self.get_style_async(style_id)
            if style:
                old_status = style.status
                style.status = status
                if adapter_path is not None:
                    style.adapter_path = adapter_path
                if self._owns_session:
                    await self.session.commit()
                logger.info(f"Style {style_id} status updated: {old_status} -> {status}")
                return True
            else:
                logger.warning(f"Style {style_id} not found for status update")
                return False
        except Exception as e:
            logger.error(f"Failed to update style {style_id} status: {e}")
            if self._owns_session:
                await self.session.rollback()
            return False

    # ==================== Evaluation Operations ====================

    def get_evaluation(self, task_id: str) -> Optional[Evaluation]:
        """Get evaluation by task ID."""
        stmt = select(Evaluation).where(Evaluation.task_id == task_id)
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_evaluation_async(self, task_id: str) -> Optional[Evaluation]:
        """Get evaluation by task ID (async)."""
        stmt = select(Evaluation).where(Evaluation.task_id == task_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def get_latest_evaluation(self, style_id: str) -> Optional[Evaluation]:
        """Get the most recent evaluation for a style."""
        stmt = select(Evaluation).where(Evaluation.style_id == style_id).order_by(Evaluation.created_at.desc()).limit(1)
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_evaluation_async(self, style_id: str) -> Optional[Evaluation]:
        """Get the most recent evaluation for a style (async)."""
        stmt = select(Evaluation).where(Evaluation.style_id == style_id).order_by(Evaluation.created_at.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def create_evaluation(self, data: Dict[str, Any]) -> Optional[Evaluation]:
        """Create a new evaluation."""
        try:
            data = dict(data)
            samples = data.get("samples")
            if samples is not None and not isinstance(samples, str):
                data["samples"] = json.dumps(samples, ensure_ascii=False)
            evaluation = Evaluation(**data)
            self.session.add(evaluation)
            if self._owns_session:
                self.session.commit()
                self.session.refresh(evaluation)
            logger.info(f"Evaluation created for task {data.get('task_id')}")
            return evaluation
        except Exception as e:
            logger.error(f"Failed to create evaluation: {e}")
            if self._owns_session:
                self.session.rollback()
            return None

    async def create_evaluation_async(self, data: Dict[str, Any]) -> Optional[Evaluation]:
        """Create a new evaluation (async)."""
        try:
            data = dict(data)
            samples = data.get("samples")
            if samples is not None and not isinstance(samples, str):
                data["samples"] = json.dumps(samples, ensure_ascii=False)
            evaluation = Evaluation(**data)
            self.session.add(evaluation)
            if self._owns_session:
                await self.session.commit()
                await self.session.refresh(evaluation)
            logger.info(f"Evaluation created for task {data.get('task_id')}")
            return evaluation
        except Exception as e:
            logger.error(f"Failed to create evaluation: {e}")
            if self._owns_session:
                await self.session.rollback()
            return None

    def update_evaluation_comment(self, task_id: str, comment: str) -> bool:
        """Update evaluation comment."""
        try:
            evaluation = self.get_evaluation(task_id)
            if evaluation:
                evaluation.comment = comment
                if self._owns_session:
                    self.session.commit()
                logger.info(f"Evaluation comment updated for task {task_id}")
                return True
            else:
                logger.warning(f"Evaluation not found for task {task_id}")
                return False
        except Exception as e:
            logger.error(f"Failed to update evaluation comment: {e}")
            if self._owns_session:
                self.session.rollback()
            return False

    async def update_evaluation_comment_async(self, task_id: str, comment: str) -> bool:
        """Update evaluation comment (async)."""
        try:
            evaluation = await self.get_evaluation_async(task_id)
            if evaluation:
                evaluation.comment = comment
                if self._owns_session:
                    await self.session.commit()
                logger.info(f"Evaluation comment updated for task {task_id}")
                return True
            else:
                logger.warning(f"Evaluation not found for task {task_id}")
                return False
        except Exception as e:
            logger.error(f"Failed to update evaluation comment: {e}")
            if self._owns_session:
                await self.session.rollback()
            return False

    # ==================== Message Operations ====================

    def get_messages(self, style_id: str, limit: Optional[int] = None) -> List[Message]:
        """Get messages for a style, optionally limited."""
        stmt = select(Message).where(Message.style_id == style_id).order_by(Message.created_at.asc())
        if limit:
            stmt = stmt.limit(limit)
        result = self.session.execute(stmt)
        return result.scalars().all()

    async def get_messages_async(self, style_id: str, limit: Optional[int] = None) -> List[Message]:
        """Get messages for a style, optionally limited (async)."""
        stmt = select(Message).where(Message.style_id == style_id).order_by(Message.created_at.asc())
        if limit:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    def create_message(self, style_id: str, data: Dict[str, Any]) -> Optional[Message]:
        """Create a new message."""
        try:
            message = Message(style_id=style_id, **data)
            self.session.add(message)
            if self._owns_session:
                self.session.commit()
                self.session.refresh(message)
            logger.debug(f"Message created for style {style_id}")
            return message
        except Exception as e:
            logger.error(f"Failed to create message: {e}")
            if self._owns_session:
                self.session.rollback()
            return None

    async def create_message_async(self, style_id: str, data: Dict[str, Any]) -> Optional[Message]:
        """Create a new message (async)."""
        try:
            message = Message(style_id=style_id, **data)
            self.session.add(message)
            if self._owns_session:
                await self.session.commit()
                await self.session.refresh(message)
            logger.debug(f"Message created for style {style_id}")
            return message
        except Exception as e:
            logger.error(f"Failed to create message: {e}")
            if self._owns_session:
                await self.session.rollback()
            return None

    def delete_messages(self, style_id: str) -> bool:
        """Delete all messages for a style."""
        try:
            stmt = select(Message).where(Message.style_id == style_id)
            result = self.session.execute(stmt)
            messages = result.scalars().all()
            for message in messages:
                self.session.delete(message)
            if self._owns_session:
                self.session.commit()
            logger.info(f"Deleted {len(messages)} messages for style {style_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete messages: {e}")
            if self._owns_session:
                self.session.rollback()
            return False

    async def delete_messages_async(self, style_id: str) -> bool:
        """Delete all messages for a style (async)."""
        try:
            stmt = select(Message).where(Message.style_id == style_id)
            result = await self.session.execute(stmt)
            messages = result.scalars().all()
            for message in messages:
                await self.session.delete(message)
            if self._owns_session:
                await self.session.commit()
            logger.info(f"Deleted {len(messages)} messages for style {style_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete messages: {e}")
            if self._owns_session:
                await self.session.rollback()
            return False

    # ==================== Combined Operations ====================

    def complete_training(self, style_id: str, task_id: str,
                         adapter_path: str) -> bool:
        """Mark training as complete - updates both style and task atomically.

        This is a combined operation that ensures both style and task are updated
        in the same transaction when possible.
        """
        try:
            style = self.get_style(style_id)
            task = self.get_task(task_id)

            if not style:
                logger.error(f"Style {style_id} not found")
                return False
            if not task:
                logger.error(f"Task {task_id} not found")
                return False

            # Update style
            style.status = "available"
            style.adapter_path = adapter_path

            # Update task
            task.status = "COMPLETED"
            task.progress = 100
            task.completed_at = datetime.utcnow()

            if self._owns_session:
                self.session.commit()

            logger.info(f"Training completed for style {style_id}, task {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to complete training: {e}")
            if self._owns_session:
                self.session.rollback()
            return False

    async def complete_training_async(self, style_id: str, task_id: str,
                                      adapter_path: str) -> bool:
        """Mark training as complete (async)."""
        try:
            style = await self.get_style_async(style_id)
            task = await self.get_task_async(task_id)

            if not style:
                logger.error(f"Style {style_id} not found")
                return False
            if not task:
                logger.error(f"Task {task_id} not found")
                return False

            # Update style
            style.status = "available"
            style.adapter_path = adapter_path

            # Update task
            task.status = "COMPLETED"
            task.progress = 100
            task.completed_at = datetime.utcnow()

            if self._owns_session:
                await self.session.commit()

            logger.info(f"Training completed for style {style_id}, task {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to complete training: {e}")
            if self._owns_session:
                await self.session.rollback()
            return False
