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
from ..db_operations import DatabaseOperations

# Create Celery app
celery_app = Celery("style_transfer")
celery_app.config_from_object("app.celery_app.celeryconfig")

# Explicitly disable mingle to speed up startup
celery_app.conf.worker_mingle = False
celery_app.conf.worker_gossip = False
celery_app.conf.broker_heartbeat = 0

# Logger
logger = get_logger(__name__)

from config import settings

APPLY_COMMENT_ADJUSTMENT = settings.APPLY_COMMENT_ADJUSTMENT

# Track missing tasks to avoid repeated error logging
_missing_tasks_cache = set()


@celery_app.task(bind=True, max_retries=1, default_retry_delay=5)
def train_style_model(
    self,
    task_id: str,
    style_id: str,
    training_text: str,
    config: dict,
    parent_style_id: str = None
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
    logger.info(f"Config: {config}")
    logger.info(f"Celery task ID: {self.request.id}")
    logger.info(f"Attempt: {self.request.retries + 1}/4")
    logger.info("=" * 60)

    # Initialize database operations
    db = DatabaseOperations()

    # Update style status to preprocessing
    db.update_style_status(style_id, "preprocessing", None)
    db.update_task_status(task_id, "PREPROCESSING")

    # Get style config for preprocessing
    style_config = {}
    try:
        style = db.get_style(style_id)
        if style:
            style_config = {
                'target_style': f"<{style.target_style}>",
                'style_name': style.name,
                'style_description': style.description or ''
            }
    except Exception as e:
        logger.warning(f"Failed to get style config: {e}")

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

        # Step 2.5: Adjust samples by parent style comment if applicable
        if parent_style_id and APPLY_COMMENT_ADJUSTMENT:
            logger.info(f"Checking for parent style comment: {parent_style_id}")
            evaluation = db.get_latest_evaluation(parent_style_id)

            if evaluation and evaluation.comment:
                logger.info(f"Found comment for parent style {parent_style_id}: {evaluation.comment[:50]}...")
                try:
                    inference_service = get_inference_service()
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
        preprocessor.save_to_jsonl(preprocessed['train_data'], f"{output_dir}/train.jsonl")
        preprocessor.save_to_jsonl(preprocessed['val_data'], f"{output_dir}/val.jsonl")
        with open(f"{output_dir}/original.txt", 'w', encoding='utf-8') as f:
            f.write(training_text)
        with open(f"{output_dir}/metadata.json", 'w', encoding='utf-8') as f:
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

        # Step 3: Verify adapter path
        logger.info(f"Step 3: Adapter saved to: {adapter_path}")

        # Step 4: Run evaluation (this sets status to EVALUATING, then COMPLETED)
        logger.info("Step 4: Running evaluation...")

        # Run evaluation using DatabaseOperations
        try:
            logger.info(f"Starting evaluation for task {task_id}")

            # Update style status to evaluating
            db.update_style_status(style_id, "evaluating", None)
            db.update_task_status(task_id, "EVALUATING")

            # Run evaluation
            inference_service = get_inference_service()
            evaluation_data = asyncio.run(evaluation_service.generate_evaluation_data(task_id, inference_service))

            # Create evaluation record
            db.create_evaluation({
                "task_id": task_id,
                "style_id": style_id,
                "task_name": db.get_task(task_id).name or "未命名任务",
                "target_style": style.target_style if style else "",
                "overall_score": evaluation_data.get("overall_score", 0),
                "sample_count": evaluation_data.get("sample_count", 0),
                # "semantic_score": evaluation_data.get("semantic_score", 0),
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

            # Complete training (updates both style and task status)
            db.complete_training(style_id, task_id, adapter_path)

            logger.info(f"Evaluation completed for task {task_id}")

        except Exception as eval_error:
            logger.error(f"Evaluation failed for task {task_id}: {eval_error}")
            # Even if evaluation fails, mark as completed (with empty evaluation)
            db.complete_training(style_id, task_id, adapter_path)

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
