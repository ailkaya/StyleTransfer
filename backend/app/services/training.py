"""Training service for style model fine-tuning.

This module contains placeholder implementation for v0.1.
In v0.2+, it will implement actual QLoRA training logic.
"""

import os
import time
import random
from datetime import datetime
from typing import Optional, Dict, Any

# QLoRA training imports
try:
    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        Trainer,
        DataCollatorForLanguageModeling,
        BitsAndBytesConfig
    )
    from peft import (
        LoraConfig,
        get_peft_model,
        prepare_model_for_kbit_training,
        TaskType
    )
    from datasets import Dataset
    QLORA_AVAILABLE = True
except ImportError:
    QLORA_AVAILABLE = False

from ..utils import get_logger
logger = get_logger(__name__)

from config import settings

TRAINING_MOCK_MODE = settings.TRAINING_MOCK_MODE

class TrainingService:
    """Service for managing style model training."""

    def __init__(self):
        self.models_dir = os.path.join(os.getcwd(), "models", "adapters")
        os.makedirs(self.models_dir, exist_ok=True)
        self.training_config = {
            "base_model": getattr(settings, 'LOCAL_BASE_MODEL', 'Qwen/Qwen2.5-7B-Instruct'),
            "lora_r": 16,
            "lora_alpha": 32,
            "lora_dropout": 0.05,
            "learning_rate": 2e-4,
            "per_device_train_batch_size": 1,
            "gradient_accumulation_steps": 4,
            "max_seq_length": 512,
            "warmup_steps": 100,
            "logging_steps": 10,
        }

    def generate_adapter_file(self, style_id: str, task_id: str) -> str:
        """
        Generate a placeholder adapter file.

        In v0.1, this creates a dummy file to simulate model output.
        In v0.2+, this will save actual LoRA adapter weights.
        """
        adapter_dir = os.path.join(self.models_dir, str(style_id))
        os.makedirs(adapter_dir, exist_ok=True)

        # Create placeholder adapter files
        adapter_path = os.path.join(adapter_dir, "adapter_config.json")
        adapter_model_path = os.path.join(adapter_dir, "adapter_model.bin")

        # Write dummy config
        config_content = f"""{{
    "adapter_type": "lora",
    "style_id": "{style_id}",
    "task_id": "{task_id}",
    "created_at": "{datetime.utcnow().isoformat()}",
    "version": "0.1.0",
    "note": "This is a placeholder adapter file for v0.1 demo purposes"
}}"""

        with open(adapter_path, "w", encoding="utf-8") as f:
            f.write(config_content)

        # Write dummy model file (just random bytes for placeholder)
        with open(adapter_model_path, "wb") as f:
            # Write ~100KB of random data as placeholder
            f.write(os.urandom(100 * 1024))

        return adapter_dir

    def training_progress(
        self,
        task_id: str,
        total_epochs: int,
        training_text: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        on_progress: Optional[callable] = None,
    ):
        """
        Main entry point for training. Dispatches to mock or true implementation.

        Args:
            task_id: Training task ID
            total_epochs: Total number of epochs
            training_text: Text data for training
            config: Training configuration dict
            on_progress: Callback function(progress_dict) for progress updates
        """
        logger.info(f"[Training] Starting train progress for task: {task_id}, mock_mode: {TRAINING_MOCK_MODE}")
        if TRAINING_MOCK_MODE:
            return self.training_progress_mock(
                task_id=task_id,
                total_epochs=total_epochs,
                on_progress=on_progress
            )
        return self.training_progress_true(
            task_id=task_id,
            total_epochs=total_epochs,
            training_text=training_text,
            config=config,
            on_progress=on_progress
        )

    def training_progress_true(
        self,
        task_id: str,
        total_epochs: int,
        training_text: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        on_progress: Optional[callable] = None,
    ):
        """
        Perform actual QLoRA training on local machine.

        Args:
            task_id: Training task ID
            total_epochs: Total number of epochs
            training_text: Text data for training
            config: Training configuration dict
            on_progress: Callback function(progress_dict) for progress updates
        """
        if not QLORA_AVAILABLE:
            raise RuntimeError(
                "QLoRA training requires transformers, peft, and datasets. "
                "Install with: pip install transformers peft datasets accelerate bitsandbytes"
            )

        if not training_text:
            raise ValueError("training_text is required for QLoRA training")

        # Merge config with defaults
        train_config = self.training_config.copy()
        if config:
            train_config.update(config)

        start_time = time.time()
        adapter_dir = os.path.join(self.models_dir, str(task_id))
        os.makedirs(adapter_dir, exist_ok=True)

        # Progress callback wrapper
        class ProgressCallback:
            def __init__(self, outer, task_id, total_epochs, start_time, on_progress):
                self.outer = outer
                self.task_id = task_id
                self.total_epochs = total_epochs
                self.start_time = start_time
                self.on_progress = on_progress
                self.current_step = 0
                self.total_steps = total_epochs * 10  # Approximate

            def on_log(self, args, state, control, logs=None, **kwargs):
                if logs and self.on_progress:
                    epoch = state.epoch or 0
                    progress = min(int((epoch / self.total_epochs) * 100), 99)

                    elapsed = int(time.time() - self.start_time)
                    if progress > 0:
                        estimated_total = elapsed / (progress / 100)
                        remaining = int(estimated_total - elapsed)
                    else:
                        remaining = 0

                    loss = logs.get('loss', 0.0)
                    current_epoch = int(epoch) + 1

                    progress_data = {
                        "task_id": self.task_id,
                        "status": "PROCESSING",
                        "progress": progress,
                        "current_epoch": min(current_epoch, self.total_epochs),
                        "total_epochs": self.total_epochs,
                        "current_loss": round(loss, 4),
                        "elapsed_time": elapsed,
                        "estimated_remaining": remaining,
                        "log_lines": [
                            f"Epoch {current_epoch}/{self.total_epochs}: training",
                            f"Loss: {loss:.4f}" if loss else "Initializing...",
                            f"Progress: {progress}%",
                            f"Elapsed: {elapsed}s",
                        ],
                    }
                    self.on_progress(progress_data)

        try:
            # Report initialization
            if on_progress:
                on_progress({
                    "task_id": task_id,
                    "status": "PROCESSING",
                    "progress": 0,
                    "current_epoch": 1,
                    "total_epochs": total_epochs,
                    "current_loss": 0.0,
                    "elapsed_time": 0,
                    "estimated_remaining": 0,
                    "log_lines": ["Loading base model..."],
                })

            # Configure quantization (4-bit)
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16
            )

            # Load tokenizer and model
            tokenizer = AutoTokenizer.from_pretrained(
                train_config["base_model"],
                trust_remote_code=True
            )
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

            if on_progress:
                on_progress({
                    "task_id": task_id,
                    "status": "PROCESSING",
                    "progress": 5,
                    "current_epoch": 1,
                    "total_epochs": total_epochs,
                    "current_loss": 0.0,
                    "elapsed_time": int(time.time() - start_time),
                    "estimated_remaining": 0,
                    "log_lines": ["Loading model with QLoRA config..."],
                })

            model = AutoModelForCausalLM.from_pretrained(
                train_config["base_model"],
                quantization_config=bnb_config,
                device_map="auto",
                trust_remote_code=True,
                torch_dtype=torch.bfloat16,
            )

            # Prepare model for k-bit training
            model = prepare_model_for_kbit_training(model)

            # Configure LoRA
            lora_config = LoraConfig(
                r=train_config["lora_r"],
                lora_alpha=train_config["lora_alpha"],
                target_modules=["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
                lora_dropout=train_config["lora_dropout"],
                bias="none",
                task_type=TaskType.CAUSAL_LM,
            )

            model = get_peft_model(model, lora_config)

            # Prepare dataset
            texts = [t.strip() for t in training_text.split('\n') if t.strip()]
            if len(texts) < 1:
                texts = [training_text]  # Use entire text as one sample

            # Create dataset
            def tokenize_function(examples):
                return tokenizer(
                    examples["text"],
                    truncation=True,
                    max_length=train_config["max_seq_length"],
                    padding="max_length"
                )

            dataset = Dataset.from_dict({"text": texts})
            tokenized_dataset = dataset.map(
                tokenize_function,
                batched=True,
                remove_columns=dataset.column_names
            )

            # Data collator
            data_collator = DataCollatorForLanguageModeling(
                tokenizer=tokenizer,
                mlm=False
            )

            # Training arguments
            training_args = TrainingArguments(
                output_dir=adapter_dir,
                num_train_epochs=total_epochs,
                per_device_train_batch_size=train_config["per_device_train_batch_size"],
                gradient_accumulation_steps=train_config["gradient_accumulation_steps"],
                warmup_steps=train_config["warmup_steps"],
                learning_rate=train_config["learning_rate"],
                logging_steps=train_config["logging_steps"],
                save_strategy="epoch",
                save_total_limit=1,
                fp16=False,
                bf16=True,
                report_to=[],
                remove_unused_columns=False,
            )

            # Progress callback
            progress_callback = ProgressCallback(
                self, task_id, total_epochs, start_time, on_progress
            )

            # Initialize trainer
            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=tokenized_dataset,
                data_collator=data_collator,
                callbacks=[],
            )

            # Add progress callback
            trainer.add_callback(progress_callback)

            # Train
            trainer.train()

            # Save final adapter
            model.save_pretrained(adapter_dir)
            tokenizer.save_pretrained(adapter_dir)

            # Training complete
            final_progress = {
                "task_id": task_id,
                "status": "COMPLETED",
                "progress": 100,
                "current_epoch": total_epochs,
                "total_epochs": total_epochs,
                "current_loss": round(trainer.state.log_history[-1].get('loss', 0.1), 4) if trainer.state.log_history else 0.1,
                "elapsed_time": int(time.time() - start_time),
                "estimated_remaining": 0,
                "log_lines": [f"Training completed in {int(time.time() - start_time)}s"],
            }

            if on_progress:
                on_progress(final_progress)

            return adapter_dir

        except Exception as e:
            # Report failure
            if on_progress:
                on_progress({
                    "task_id": task_id,
                    "status": "FAILED",
                    "progress": 0,
                    "current_epoch": 0,
                    "total_epochs": total_epochs,
                    "current_loss": 0.0,
                    "elapsed_time": int(time.time() - start_time),
                    "estimated_remaining": 0,
                    "log_lines": [f"Training failed: {str(e)}"],
                })
            raise RuntimeError(f"QLoRA training failed: {str(e)}")

    def training_progress_mock(
        self,
        task_id: str,
        total_epochs: int,
        on_progress: Optional[callable] = None,
    ):
        """
        Simulate training progress for v0.1.

        In v0.2+, this will be replaced with actual QLoRA training loop.

        Args:
            task_id: Training task ID
            total_epochs: Total number of epochs
            on_progress: Callback function(progress_dict) for progress updates
        """
        start_time = time.time()

        for epoch in range(1, total_epochs + 1):
            # Simulate epoch processing time
            epoch_start = time.time()

            # Simulate progress through the epoch
            steps = 10
            for step in range(steps):
                time.sleep(3)  # Simulate work

                # Calculate overall progress
                epoch_progress = (step + 1) / steps
                overall_progress = int(((epoch - 1 + epoch_progress) / total_epochs) * 100)

                # Simulate loss (decreasing)
                current_loss = 1.0 - (overall_progress / 100) * 0.5 + random.uniform(-0.05, 0.05)
                current_loss = max(0.1, current_loss)

                # Calculate times
                elapsed = int(time.time() - start_time)
                if overall_progress > 0:
                    estimated_total = elapsed / (overall_progress / 100)
                    remaining = int(estimated_total - elapsed)
                else:
                    remaining = 0

                # Generate log lines
                log_lines = [
                    f"Epoch {epoch}/{total_epochs}: Step {step + 1}/{steps}",
                    f"Loss: {current_loss:.4f}",
                    f"Progress: {overall_progress}%",
                    f"Elapsed: {elapsed}s",
                ]

                progress_data = {
                    "task_id": task_id,
                    "status": "PROCESSING",
                    "progress": overall_progress,
                    "current_epoch": epoch,
                    "total_epochs": total_epochs,
                    "current_loss": round(current_loss, 4),
                    "elapsed_time": elapsed,
                    "estimated_remaining": remaining,
                    "log_lines": log_lines,
                }

                if on_progress:
                    on_progress(progress_data)

            # Epoch complete
            epoch_time = time.time() - epoch_start

        # Training complete
        final_progress = {
            "task_id": task_id,
            "status": "COMPLETED",
            "progress": 100,
            "current_epoch": total_epochs,
            "total_epochs": total_epochs,
            "current_loss": round(random.uniform(0.1, 0.3), 4),
            "elapsed_time": int(time.time() - start_time),
            "estimated_remaining": 0,
            "log_lines": [f"Training completed in {int(time.time() - start_time)}s"],
        }

        if on_progress:
            on_progress(final_progress)

        return final_progress


# Global training service instance
training_service = TrainingService()
