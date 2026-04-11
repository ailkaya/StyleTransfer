"""Celery tasks for style model training."""

import os
import json
from datetime import datetime
from celery import Celery
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
import redis

from ..models import Task
from ..services import training_service, preprocessing_service
from ..utils import get_logger

# Create Celery app
celery_app = Celery("style_transfer")
celery_app.config_from_object("app.celery_app.celeryconfig")

# Explicitly disable mingle to speed up startup
celery_app.conf.worker_mingle = False
celery_app.conf.worker_gossip = False
celery_app.conf.broker_heartbeat = 0

# Logger
logger = get_logger(__name__)

# Database setup for sync context (Celery runs synchronously)
# We'll use sync database operations in Celery tasks
SYNC_DATABASE_URL = os.getenv(
    "SYNC_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/style_transfer"
)
from sqlalchemy import create_engine

# Lazy initialization to avoid import delays
_sync_engine = None
_SyncSessionLocal = None

def get_sync_engine():
    global _sync_engine
    if _sync_engine is None:
        logger.debug("Creating sync database engine...")
        _sync_engine = create_engine(SYNC_DATABASE_URL)
        logger.debug("Sync database engine created")
    return _sync_engine

def get_sync_session():
    global _SyncSessionLocal
    if _SyncSessionLocal is None:
        logger.debug("Creating sync session factory...")
        _SyncSessionLocal = sessionmaker(bind=get_sync_engine())
        logger.debug("Sync session factory created")
    return _SyncSessionLocal()

# Redis for WebSocket notifications (lazy initialization)
_redis_client = None

def get_redis_client():
    global _redis_client
    if _redis_client is None:
        logger.debug("Initializing Redis client for Celery tasks...")
        try:
            _redis_client = redis.Redis.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            _redis_client.ping()
            logger.info("Redis client initialized and connected")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            _redis_client = None
    return _redis_client

logger.info("Celery tasks module loaded")


def publish_progress_update(task_id: str, progress_data: dict):
    """Publish progress update to Redis for WebSocket consumers."""
    client = get_redis_client()
    if client is None:
        logger.warning(f"Redis not available, skipping progress publish for task {task_id}")
        return

    try:
        message = {
            "type": "progress",
            "task_id": task_id,
            "data": progress_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        channel = f"task:{task_id}"
        result = client.publish(channel, json.dumps(message))
        logger.debug(f"Published progress to {channel}, subscribers: {result}")
    except Exception as e:
        logger.error(f"Failed to publish progress update for task {task_id}: {e}")


# Track missing tasks to avoid repeated error logging
_missing_tasks_cache = set()

def update_task_progress(task_id: str, progress_data: dict):
    """Update task progress in database and notify via Redis."""
    # Skip if we already know this task is missing
    if task_id in _missing_tasks_cache:
        return False

    logger.debug(f"Updating progress for task {task_id}: {progress_data.get('status')} - {progress_data.get('progress')}%")

    session = get_sync_session()
    try:
        stmt = select(Task).where(Task.id == task_id)
        result = session.execute(stmt)
        task = result.scalar_one_or_none()

        if task:
            old_status = task.status
            old_progress = task.progress

            task.status = progress_data.get("status", task.status)
            task.progress = progress_data.get("progress", task.progress)
            task.current_epoch = progress_data.get("current_epoch")
            task.current_loss = progress_data.get("current_loss")
            task.elapsed_time = progress_data.get("elapsed_time")
            task.estimated_remaining = progress_data.get("estimated_remaining")

            # Note: logs are no longer saved to database, only published via Redis

            if progress_data.get("status") in ["COMPLETED", "FAILED"]:
                task.completed_at = datetime.utcnow()

            session.commit()

            logger.debug(
                f"Task {task_id} updated: {old_status}({old_progress}%) -> "
                f"{task.status}({task.progress}%)"
            )

            # Publish to Redis for WebSocket broadcast
            publish_progress_update(task_id, progress_data)
            return True
        else:
            # Only log error once per task
            if task_id not in _missing_tasks_cache:
                _missing_tasks_cache.add(task_id)
                logger.error(f"Task {task_id} not found in database. Subsequent updates will be skipped.")
            return False
    except Exception as e:
        logger.error(f"Failed to update task {task_id} progress: {e}", exc_info=True)
        session.rollback()
        raise
    finally:
        session.close()


def update_task_result(task_id: str, adapter_path: str = None, error: str = None):
    """Update task result after completion."""
    logger.info(f"Updating task result for {task_id}: adapter_path={adapter_path is not None}, error={error is not None}")

    session = get_sync_session()
    try:
        stmt = select(Task).where(Task.id == task_id)
        result = session.execute(stmt)
        task = result.scalar_one_or_none()

        if task:
            if adapter_path:
                task.result_path = adapter_path
                task.status = "COMPLETED"
                task.progress = 100

                # Update style status
                from ..models import Style
                style_stmt = select(Style).where(Style.id == task.style_id)
                style_result = session.execute(style_stmt)
                style = style_result.scalar_one_or_none()
                if style:
                    old_style_status = style.status
                    style.status = "available"
                    style.adapter_path = adapter_path
                    logger.info(f"Style {task.style_id} status updated: {old_style_status} -> available")

            if error:
                task.error_message = error
                task.status = "FAILED"

            task.completed_at = datetime.utcnow()
            session.commit()

            logger.info(f"Task {task_id} completed with status: {task.status}")

            # Publish completion notification to Redis
            progress_data = {
                "status": task.status,
                "progress": 100 if adapter_path else 0,
                # Note: log_lines no longer saved to database
            }
            if error:
                progress_data["error"] = error
            publish_progress_update(task_id, progress_data)
        else:
            # Only log error once per task
            if task_id not in _missing_tasks_cache:
                _missing_tasks_cache.add(task_id)
                logger.error(f"Task {task_id} not found when updating result")
    except Exception as e:
        logger.error(f"Failed to update task {task_id} result: {e}", exc_info=True)
        session.rollback()
        raise
    finally:
        session.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def train_style_model(self, task_id: str, style_id: str, training_text: str, config: dict):
    """
    Celery task for training style model.

    In v0.1, this simulates training progress.
    In v0.2+, this will implement actual QLoRA training.
    """
    # Clear from missing tasks cache (in case of retry)
    if task_id in _missing_tasks_cache:
        _missing_tasks_cache.discard(task_id)
        logger.debug(f"Cleared task {task_id} from missing tasks cache")

    logger.info("=" * 60)
    logger.info(f"Starting training task: {task_id}")
    logger.info(f"Style ID: {style_id}")
    logger.info(f"Training text length: {len(training_text)} chars")
    logger.info(f"Config: {config}")
    logger.info(f"Celery task ID: {self.request.id}")
    logger.info(f"Attempt: {self.request.retries + 1}/4")
    logger.info("=" * 60)

    try:
        # Preprocess training text
        logger.info("Step 1: Preprocessing training text...")
        preprocessed = preprocessing_service.preprocess_training_text(
            training_text,
            chunk_size=config.get("max_length", 512),
            overlap=128,
        )
        logger.info(f"Preprocessing complete:")
        logger.info(f"  - Chunks: {preprocessed['chunk_count']}")
        logger.info(f"  - Estimated tokens: {preprocessed['estimated_tokens']}")
        logger.info(f"  - Cleaned text length: {len(preprocessed['cleaned_text'])} chars")

        # Update initial status
        update_task_progress(task_id, {
            "status": "PROCESSING",
            "progress": 0,
        })
        # Note: Logs are published via Redis for real-time display, not saved to database

        # Simulate training
        logger.info("Step 2: Starting training simulation...")
        total_epochs = config.get("num_epochs", 3)
        logger.info(f"Total epochs to simulate: {total_epochs}")

        def on_progress(progress_data):
            logger.debug(
                f"Epoch {progress_data.get('current_epoch')}/{total_epochs}: "
                f"{progress_data.get('progress')}% - Loss: {progress_data.get('current_loss')}"
            )
            # Publish logs via Redis for real-time display, but don't save to database
            publish_progress_update(task_id, progress_data)

            # Strip log_lines before saving to database
            db_progress_data = {k: v for k, v in progress_data.items() if k != "log_lines"}
            updated = update_task_progress(task_id, db_progress_data)
            if not updated:
                # Task not found in database, stop training
                raise RuntimeError(f"Task {task_id} not found in database, stopping training")

        training_service.simulate_training_progress(
            task_id=task_id,
            total_epochs=total_epochs,
            on_progress=on_progress,
        )
        logger.info("Training simulation completed")

        # Generate placeholder adapter
        logger.info("Step 3: Generating adapter file...")
        adapter_path = training_service.generate_adapter_file(style_id, task_id)
        logger.info(f"Adapter file generated: {adapter_path}")

        # Update final result
        logger.info("Step 4: Updating task result...")
        update_task_result(task_id, adapter_path=adapter_path)

        logger.info("=" * 60)
        logger.info(f"Training task {task_id} completed successfully")
        logger.info("=" * 60)

        return {
            "task_id": task_id,
            "status": "COMPLETED",
            "adapter_path": adapter_path,
        }

    except Exception as exc:
        error_msg = str(exc)
        logger.error(f"Training task {task_id} failed: {error_msg}", exc_info=True)
        update_task_result(task_id, error=error_msg)

        # Retry on failure
        if self.request.retries < 3:
            retry_countdown = 60 * (self.request.retries + 1)
            logger.warning(f"Retrying task {task_id} in {retry_countdown}s (attempt {self.request.retries + 2}/4)")
            raise self.retry(exc=exc, countdown=retry_countdown)

        logger.error(f"Task {task_id} failed after all retries")
        return {
            "task_id": task_id,
            "status": "FAILED",
            "error": error_msg,
        }
