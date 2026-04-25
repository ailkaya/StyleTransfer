"""Celery tasks for style model training."""

import os
import json
import asyncio
from datetime import datetime
from celery import Celery
from celery.signals import worker_process_shutdown
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

from ..models import Task, Style, Evaluation
from ..services import training_service, evaluation_service, get_inference_service, DataPreprocessor
from ..utils import get_logger
from ..db_operations import DatabaseOperations
from config import settings

# Create Celery app
celery_app = Celery("style_transfer")
celery_app.config_from_object("app.celery_app.celeryconfig")

# Explicitly disable mingle to speed up startup
celery_app.conf.worker_mingle = False
celery_app.conf.worker_gossip = False
celery_app.conf.broker_heartbeat = 0


@worker_process_shutdown.connect
def _cleanup_models_on_worker_shutdown(**kwargs):
    """Unload all models when Celery worker process shuts down."""
    try:
        from ..services.model_manager import model_manager
        count = model_manager.unload_all()
        logger.info(f"[Celery] ModelManager unloaded {count} items on worker shutdown")
    except Exception as e:
        logger.error(f"[Celery] ModelManager shutdown cleanup failed: {e}")

# Logger
logger = get_logger(__name__)

from config import settings

APPLY_COMMENT_ADJUSTMENT = settings.APPLY_COMMENT_ADJUSTMENT

# Track missing tasks to avoid repeated error logging
_missing_tasks_cache = set()


def run_evaluation(task_id: str, style_id: str, db: DatabaseOperations, adapter_path: str = None):
    """Run evaluation for a task and save results to database.

    Args:
        task_id: The task ID to evaluate.
        style_id: The style ID associated with the task.
        db: DatabaseOperations instance.
        adapter_path: Optional adapter path. If provided, will call complete_training after evaluation.

    Returns:
        The evaluation data dictionary.
    """
    logger.info(f"Starting evaluation for task {task_id}")

    # Update style status to evaluating
    db.update_style_status(style_id, "evaluating", None)
    db.update_task_status(task_id, "EVALUATING")

    # Run evaluation
    inference_service = get_inference_service()
    evaluation_data = asyncio.run(evaluation_service.generate_evaluation_data(task_id, inference_service))

    task = db.get_task(task_id)
    style = db.get_style(style_id)

    # Delete existing evaluation if any (for re-evaluation)
    existing = db.get_evaluation(task_id)
    if existing:
        db.session.delete(existing)
        if db._owns_session:
            db.session.commit()
        logger.info(f"Deleted existing evaluation for task {task_id}")

    # Create evaluation record
    db.create_evaluation({
        "task_id": task_id,
        "style_id": style_id,
        "task_name": task.name or "未命名任务",
        "target_style": style.target_style if style else "",
        "overall_score": evaluation_data.get("overall_score", 0),
        "sample_count": evaluation_data.get("sample_count", 0),
        "char_retention": evaluation_data.get("char_retention", 0),
        "style_score": evaluation_data.get("style_score", 0),
        "fluency_score": evaluation_data.get("fluency_score", 0),
        "vocab_diversity": evaluation_data.get("vocab_diversity", 0),
        "length_ratio": evaluation_data.get("length_ratio", 0),
        "bleu_score": evaluation_data.get("bleu_score", 0),
        "bert_score": evaluation_data.get("bert_score", 0),
        "avg_response_time": evaluation_data.get("avg_response_time", 0),
        "samples": evaluation_data.get("samples", [])
    })

    if adapter_path is not None:
        db.complete_training(style_id, task_id, adapter_path)

    logger.info(f"Evaluation completed for task {task_id}")
    return evaluation_data


@celery_app.task(bind=True, max_retries=1, default_retry_delay=5)
def re_evaluate_task(self, task_id: str):
    """Celery task for re-evaluating a completed task."""
    logger.info(f"Starting re-evaluation for task: {task_id}")

    db = DatabaseOperations()
    try:
        if not db.task_exists(task_id=task_id):
            logger.warning(f"Task {task_id} not found, re-evaluation terminate")
            return

        task = db.get_task(task_id)
        if task.status != "COMPLETED":
            logger.warning(f"Task {task_id} is not completed (status={task.status}), cannot re-evaluate")
            return

        style_id = task.style_id
        run_evaluation(task_id, style_id, db)

        db.update_style_status(style_id, "available", None)
        db.update_task_status(task_id, "COMPLETED")

        logger.info(f"Re-evaluation completed for task {task_id}")
        return {
            "task_id": task_id,
            "status": "COMPLETED",
        }

    except Exception as exc:
        error_msg = str(exc)
        logger.error(f"Re-evaluation task {task_id} failed: {error_msg}", exc_info=True)
        # Restore task to COMPLETED even on failure
        db.update_task_status(task_id, "COMPLETED")
        if self.request.retries < 1:
            raise self.retry(exc=exc, countdown=30)
        return {
            "task_id": task_id,
            "status": "FAILED",
            "error": error_msg,
        }
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=1, default_retry_delay=5)
def train_style_model(
    self,
    task_id: str,
    style_id: str,
    training_text: str,
    config: dict,
    parent_style_id: str = None,
    source_text: str = None
):
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
    if source_text:
        logger.info(f"Source text length: {len(source_text)} chars")
    logger.info(f"Config: {config}")
    logger.info(f"Celery task ID: {self.request.id}")
    logger.info(f"Attempt: {self.request.retries + 1}/4")
    logger.info("=" * 60)

    # Initialize database operations
    db = DatabaseOperations()

    if not db.task_exists(task_id=task_id):
        logger.warning(f"Task {task_id} not found, task terminate")
        return
    
    task = db.get_task(task_id=task_id)
    if task.status == 'COMPLETED':
        logger.info(f"Task {task_id} COMPLETED")
        return

    # Update style status to preprocessing
    db.update_style_status(style_id, "preprocessing", None)
    db.update_task_status(task_id, "PREPROCESSING")

    # Get style config for preprocessing
    style_config = {}
    try:
        style = db.get_style(style_id)
        if style:
            style_config = {
                'target_style': f"{style.target_style}",
                'style_name': style.name,
                'style_description': style.description or ''
            }
    except Exception as e:
        logger.warning(f"Failed to get style config: {e}")
        return

    training_text_path = None
    source_text_path = None

    # Persist raw training text to temp file before preprocessing
    try:
        training_text_dir = "./training_text"
        os.makedirs(training_text_dir, exist_ok=True)
        training_text_path = os.path.join(training_text_dir, f"{task_id}.txt")
        with open(training_text_path, 'w', encoding='utf-8') as f:
            f.write(training_text)
        db.update_task_training_text_path(task_id, training_text_path)
        db.update_task_parent_style_id(task_id, parent_style_id)
        logger.info(f"Saved training_text to {training_text_path}")
    except Exception as e:
        logger.error(f"Failed to persist training_text for task {task_id}: {e}")

    # Persist source text to temp file if provided
    if source_text:
        try:
            source_text_path = os.path.join(training_text_dir, f"{task_id}_source.txt")
            with open(source_text_path, 'w', encoding='utf-8') as f:
                f.write(source_text)
            logger.info(f"Saved source_text to {source_text_path}")
        except Exception as e:
            logger.error(f"Failed to persist source_text for task {task_id}: {e}")

    try:
        # Preprocess training text using DataPreprocessor
        logger.info("Step 1: Preprocessing training text with DataPreprocessor...")

        # Initialize preprocessor with style config
        preprocessor = DataPreprocessor(
            style_config=style_config,
        )

        # Run full preprocessing pipeline
        inference_service = get_inference_service()
        process_kwargs = {
            "raw_text": training_text,
            "source_text": source_text,
            "inference_service": inference_service,
            "train_ratio": 0.95,
        }
        if settings.SIMPLE_PREPROCESSING:
            process_kwargs.update({
                "style_transfer_num": 1,
                "continuation_samples_num": 1,
                "generation_samples_num": 1,
                "explanation_samples_num": 1,
                "summarization_samples_num": 1,
            })
        preprocessed = asyncio.run(preprocessor.process(**process_kwargs))

        logger.info(f"Preprocessing complete:")
        logger.info(f"  - Language: {preprocessed['metadata']['language']}")
        logger.info(f"  - Chunks: {preprocessed['metadata']['chunk_count']}")
        logger.info(f"  - Samples: {preprocessed['metadata']['sample_count']}")
        logger.info(f"  - Train samples: {len(preprocessed['train_data'])}")
        logger.info(f"  - Val samples: {len(preprocessed['val_data'])}")
        logger.info(f"  - Data length: {preprocessed['metadata']['original_length']:.0f} chars")

        # Step 2.5: Adjust samples by parent style comment if applicable
        if parent_style_id and APPLY_COMMENT_ADJUSTMENT:
            logger.info(f"Checking for parent style comment: {parent_style_id}")
            evaluation = db.get_latest_evaluation(parent_style_id)

            if evaluation and evaluation.comment:
                logger.info(f"Found comment for parent style {parent_style_id}: {evaluation.comment[:50]}...")
                try:
                    adjusted_train_data = asyncio.run(preprocessor.adjust_samples_by_comment(
                        preprocessed['train_data'], evaluation.comment, inference_service
                    ))
                    adjusted_count = sum(1 for s in adjusted_train_data if s.get('metadata', {}).get('adjusted_by_comment'))
                    logger.info(f"Adjusted {adjusted_count} samples based on comment")
                    preprocessed['train_data'] = adjusted_train_data
                except Exception as e:
                    logger.error(f"Failed to adjust samples by comment: {e}")
            else:
                logger.info(f"No comment found for parent style {parent_style_id}")

        # Save processed data for training (optional, for debugging)
        output_dir = f"./training_data/{task_id}"
        os.makedirs(output_dir, exist_ok=True)
        preprocessor.save_to_jsonl(preprocessed['train_data'], os.path.join(output_dir, "train.jsonl"))
        preprocessor.save_to_jsonl(preprocessed['val_data'], os.path.join(output_dir, "val.jsonl"))
        with open(os.path.join(output_dir, "cleaned_text.txt"), 'w', encoding='utf-8') as f:
            f.write(preprocessed.get('cleaned_text', ''))
        with open(os.path.join(output_dir, "original.txt"), 'w', encoding='utf-8') as f:
            f.write(training_text)
        with open(os.path.join(output_dir, "metadata.json"), 'w', encoding='utf-8') as f:
            json.dump(preprocessed['metadata'], f, ensure_ascii=False, indent=2)
        logger.info(f"  - Saved training data to: {output_dir}")

        # Save training data path to database
        try:
            db.update_task_training_data_path(task_id, output_dir)
            logger.info(f"  - Updated task training_data_path: {output_dir}")
        except Exception as e:
            logger.error(f"Failed to update training_data_path: {e}")

        db.update_style_status(style_id, "processing", None)
        # Update initial status
        updated = db.update_task_progress(task_id, {
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
            updated = db.update_task_progress(task_id, db_progress_data)
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

        # Update adapter path in styles table
        db.update_style_status(style_id, "processing", adapter_path)

        # Step 3: Verify adapter path
        logger.info(f"Step 3: Adapter saved to: {adapter_path}")

        # Step 4: Run evaluation (this sets status to EVALUATING, then COMPLETED)
        logger.info("Step 4: Running evaluation...")
        run_evaluation(task_id, style_id, db, adapter_path=adapter_path)

        logger.info("=" * 60)
        logger.info(f"Training task {task_id} completed successfully with evaluation")
        logger.info("=" * 60)

        db.update_style_status(style_id, "available", None)
        db.update_task_status(task_id, "COMPLETED")

        return {
            "task_id": task_id,
            "status": "COMPLETED",
            "adapter_path": adapter_path,
        }

    except Exception as exc:
        error_msg = str(exc)
        logger.error(f"Training task {task_id} failed: {error_msg}", exc_info=True)
        db.update_task_result(task_id, error=error_msg)
        db.update_style_status(style_id, "failed", None)

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
    finally:
        # Close database session
        db.close()
        # Delete temporary training text file if it exists
        if training_text_path and os.path.exists(training_text_path):
            try:
                os.remove(training_text_path)
                logger.info(f"Removed training_text temp file: {training_text_path}")
            except Exception as e:
                logger.warning(f"Failed to remove training_text temp file: {e}")
        # Delete temporary source text file if it exists
        if source_text_path and os.path.exists(source_text_path):
            try:
                os.remove(source_text_path)
                logger.info(f"Removed source_text temp file: {source_text_path}")
            except Exception as e:
                logger.warning(f"Failed to remove source_text temp file: {e}")


def recover_pending_tasks():
    """Recover and re-dispatch non-terminal training tasks on startup."""
    db = DatabaseOperations()
    try:
        tasks = db.get_non_terminal_tasks()
        if not tasks:
            logger.info("No non-terminal tasks to recover")
            return

        logger.info(f"Found {len(tasks)} non-terminal tasks to recover")
        for task in tasks:
            task_id = str(task.id)
            style_id = str(task.style_id)

            training_text_path = task.training_text_path
            if not training_text_path or not os.path.exists(training_text_path):
                logger.warning(
                    f"Task {task_id} training_text not found at {training_text_path}, marking FAILED"
                )
                db.update_task_result(task_id, error="Training text temp file missing on recovery")
                continue

            with open(training_text_path, 'r', encoding='utf-8') as f:
                training_text = f.read()

            # Try to load source text if exists
            source_text = None
            source_text_path = os.path.join(os.path.dirname(training_text_path), f"{task_id}_source.txt")
            if os.path.exists(source_text_path):
                try:
                    with open(source_text_path, 'r', encoding='utf-8') as f:
                        source_text = f.read()
                    logger.info(f"Recovered source_text for task {task_id}: {len(source_text)} chars")
                except Exception as e:
                    logger.warning(f"Failed to read source_text for task {task_id}: {e}")

            db.update_task_status(task_id, "PENDING")
            db.update_style_status(style_id, "pending", None)

            config = task.config or {}
            parent_style_id = task.parent_style_id
            train_style_model.delay(
                task_id=task_id,
                style_id=style_id,
                training_text=training_text,
                source_text=source_text,
                config=config,
                parent_style_id=parent_style_id,
            )
            logger.info(f"Re-dispatched recovered task {task_id} (style={style_id})")

    except Exception as e:
        logger.error(f"Task recovery failed: {e}", exc_info=True)
    finally:
        db.close()
