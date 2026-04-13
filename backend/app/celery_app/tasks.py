"""Celery tasks for style model training."""

import os
import json
import asyncio
from datetime import datetime
from celery import Celery
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

from ..models import Task, Style, Evaluation
from ..services import training_service, preprocessing_service, evaluation_service, get_inference_service, DataPreprocessor
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

logger.info("Celery tasks module loaded")


# Track missing tasks to avoid repeated error logging
_missing_tasks_cache = set()

def update_task_progress(task_id: str, progress_data: dict):
    """Update task progress in database."""
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

            if progress_data.get("status") in ["COMPLETED", "FAILED"]:
                task.completed_at = datetime.utcnow()

            session.commit()

            logger.debug(
                f"Task {task_id} updated: {old_status}({old_progress}%) -> "
                f"{task.status}({task.progress}%)"
            )

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


def update_style_status(style_id: str, status: str, adapter_path: str = None) -> bool:
    """
    Update style status in database.

    Args:
        style_id: Style ID
        status: New status (pending, preprocessing, training, evaluating, available, failed)
        adapter_path: Optional adapter path to set

    Returns:
        True if successful, False otherwise
    """
    session = get_sync_session()
    try:
        stmt = select(Style).where(Style.id == style_id)
        result = session.execute(stmt)
        style = result.scalar_one_or_none()

        if style:
            old_status = style.status
            style.status = status
            if adapter_path is not None:
                style.adapter_path = adapter_path
            session.commit()
            logger.info(f"Style {style_id} status updated: {old_status} -> {status}")
            return True
        else:
            logger.warning(f"Style {style_id} not found for status update")
            return False
    except Exception as e:
        logger.error(f"Failed to update style {style_id} status: {e}")
        session.rollback()
        return False
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
                    update_style_status(task.style_id, "available", adapter_path)

            if error:
                task.error_message = error
                task.status = "FAILED"

            task.completed_at = datetime.utcnow()
            session.commit()

            logger.info(f"Task {task_id} completed with status: {task.status}")
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


def run_evaluation_and_save(task_id: str, style_id: str, adapter_path: str):
    """Run evaluation after training and save results to database."""
    logger.info(f"Starting evaluation for task {task_id}")

    session = get_sync_session()
    try:
        # Set status to EVALUATING
        stmt = select(Task).where(Task.id == task_id)
        result = session.execute(stmt)
        task = result.scalar_one_or_none()

        if not task:
            logger.error(f"Task {task_id} not found for evaluation")
            return

        task.status = "EVALUATING"

        # Update style status to evaluating
        style_stmt = select(Style).where(Style.id == style_id)
        style_result = session.execute(style_stmt)
        style = style_result.scalar_one_or_none()

        update_style_status(style_id, "evaluating")

        # Run evaluation using mock data for now
        # In production, this would use the actual inference service
        try:
            inference_service = get_inference_service()
            evaluation_data = asyncio.run(evaluation_service.generate_evaluation_data(task_id, inference_service))

            # Save evaluation data to separate Evaluation table
            import json
            evaluation = Evaluation(
                task_id=task_id,
                style_id=style_id,
                task_name=task.name or "未命名任务",
                target_style=style.target_style if style else "",
                overall_score=evaluation_data.get("overall_score", 0),
                sample_count=evaluation_data.get("sample_count", 0),
                semantic_score=evaluation_data.get("semantic_score", 0),
                char_retention=evaluation_data.get("char_retention", 0),
                style_score=evaluation_data.get("style_score", 0),
                fluency_score=evaluation_data.get("fluency_score", 0),
                vocab_diversity=evaluation_data.get("vocab_diversity", 0),
                length_ratio=evaluation_data.get("length_ratio", 0),
                avg_response_time=evaluation_data.get("avg_response_time", 0),
                samples=json.dumps(evaluation_data.get("samples", []))
            )
            session.add(evaluation)

            task.status = "COMPLETED"
            task.progress = 100
            task.completed_at = datetime.utcnow()

            session.commit()

            # Update style to available
            update_style_status(style_id, "available", adapter_path)

            logger.info(f"Evaluation completed for task {task_id}")

        except Exception as eval_error:
            logger.error(f"Evaluation failed for task {task_id}: {eval_error}")
            # Even if evaluation fails, mark as completed (with empty evaluation)
            task.status = "COMPLETED"
            task.evaluation_data = None
            task.completed_at = datetime.utcnow()

            session.commit()

            update_style_status(style_id, "available", adapter_path)

    except Exception as e:
        logger.error(f"Failed to run evaluation for task {task_id}: {e}")
        session.rollback()
        raise
    finally:
        session.close()


@celery_app.task(bind=True, max_retries=1, default_retry_delay=5)
def train_style_model(self, task_id: str, style_id: str, training_text: str, config: dict):
    """
    Celery task for training style model.
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

    # Update style status to preprocessing
    update_style_status(style_id, "preprocessing")

    # Get style config for preprocessing
    session = get_sync_session()
    style_config = {}
    try:
        style_stmt = select(Style).where(Style.id == style_id)
        style_result = session.execute(style_stmt)
        style = style_result.scalar_one_or_none()
        if style:
            style_config = {
                'target_style': f"<{style.target_style}>",
                'style_name': style.name,
                'style_description': style.description or ''
            }
    finally:
        session.close()

    try:
        # Preprocess training text using DataPreprocessor
        logger.info("Step 1: Preprocessing training text with DataPreprocessor...")

        # Initialize preprocessor with style config
        preprocessor = DataPreprocessor(style_config=style_config)

        # Run full preprocessing pipeline
        preprocessed = preprocessor.process(
            raw_text=training_text,
            target_length=config.get("chunk_size", 1024),
            overlap=config.get("chunk_overlap", 256),
            train_ratio=0.95
        )

        logger.info(f"Preprocessing complete:")
        logger.info(f"  - Language: {preprocessed['metadata']['language']}")
        logger.info(f"  - Chunks: {preprocessed['metadata']['chunk_count']}")
        logger.info(f"  - Samples: {preprocessed['metadata']['sample_count']}")
        logger.info(f"  - Train samples: {len(preprocessed['train_data'])}")
        logger.info(f"  - Val samples: {len(preprocessed['val_data'])}")
        logger.info(f"  - Avg length: {preprocessed['metadata']['avg_length']:.0f} chars")

        # Save processed data for training (optional, for debugging)
        output_dir = f"./training_data/{task_id}"
        os.makedirs(output_dir, exist_ok=True)
        preprocessor.save_to_jsonl(preprocessed['train_data'], f"{output_dir}/train.jsonl")
        preprocessor.save_to_jsonl(preprocessed['val_data'], f"{output_dir}/val.jsonl")
        with open(f"{output_dir}/metadata.json", 'w', encoding='utf-8') as f:
            json.dump(preprocessed['metadata'], f, ensure_ascii=False, indent=2)
        logger.info(f"  - Saved training data to: {output_dir}")

        # Update initial status
        updated = update_task_progress(task_id, {
            "status": "PROCESSING",
            "progress": 0,
        })
        if not updated:
            # Task not found in database, log and return
            logger.error(f"Task {task_id} not found in database, stopping training")
            return {
                "task_id": task_id,
                "status": "FAILED",
                "error": f"Task {task_id} not found in database"
            }

        # Start training
        logger.info("Step 2: Starting QLoRA training...")
        total_epochs = config.get("num_epochs", 3)
        logger.info(f"Total epochs: {total_epochs}")

        def on_progress(progress_data):
            logger.debug(
                f"Epoch {progress_data.get('current_epoch')}/{total_epochs}: "
                f"{progress_data.get('progress')}% - Loss: {progress_data.get('current_loss')}"
            )

            # Strip log_lines before saving to database
            db_progress_data = {k: v for k, v in progress_data.items() if k != "log_lines"}
            updated = update_task_progress(task_id, db_progress_data)
            if not updated:
                # Task not found in database, log and skip progress update
                logger.warning(f"Task {task_id} not found in database, skipping progress update")

        adapter_path = training_service.training_progress(
            task_id=task_id,
            total_epochs=total_epochs,
            training_text=preprocessed['train_data'],  # Use formatted training samples
            validation_text=preprocessed['val_data'],  # Use validation samples
            config=config,
            on_progress=on_progress,
        )
        logger.info("Training completed")

        # Step 3: Verify adapter path
        logger.info(f"Step 3: Adapter saved to: {adapter_path}")

        # Step 4: Run evaluation (this sets status to EVALUATING, then COMPLETED)
        logger.info("Step 4: Running evaluation...")
        run_evaluation_and_save(task_id, style_id, adapter_path)

        logger.info("=" * 60)
        logger.info(f"Training task {task_id} completed successfully with evaluation")
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
