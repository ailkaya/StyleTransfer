"""Training service for style model fine-tuning.

This module contains placeholder implementation for v0.1.
In v0.2+, it will implement actual QLoRA training logic.
"""

import os
import time
import random
from datetime import datetime
from typing import Optional, Dict, Any

from ..utils import get_logger, clean_and_filter_dataset, BASE_MODEL_MAP
from .model_manager import model_manager
logger = get_logger(__name__)

from config import settings

TRAINING_MOCK_MODE = settings.TRAINING_MOCK_MODE

class TrainingService:
    """Service for managing style model training."""

    def __init__(self):
        self.models_dir = os.path.join(os.getcwd(), "models", "adapters")
        os.makedirs(self.models_dir, exist_ok=True)
        self.training_config = {

            # ===== LoRA相关 =====

            "lora_r": 8,
            # LoRA的秩（rank），决定低秩矩阵的维度
            # ↑ r → 模型表达能力更强（能学更复杂风格）
            # ↑ r → 显存占用增加、过拟合风险增加
            # 常用：8（轻量） / 16（推荐） / 32（高质量任务）

            # "lora_alpha": 32,
            # LoRA缩放系数（scaling factor）
            # 实际生效强度 = alpha / r
            # ↑ alpha → LoRA更新对模型影响更大
            # 一般设置为 2 × r（如16→32）

            "lora_dropout": 0.12,
            # LoRA层的dropout概率
            # 防止过拟合（尤其小数据集很重要）
            # 常用：0.05 ~ 0.1


            # ===== 训练轮数 =====

            "num_epochs": 3,
            # 训练轮数（整个数据集重复训练的次数）
            # ↑ epoch → 更容易收敛，但可能过拟合
            # 小数据：3~5，大数据：1~3


            # ===== 学习率相关 =====

            "learning_rate": 1e-4,
            # 初始学习率（LoRA训练通常比全参数训练大）
            # ↑ lr → 收敛更快，但可能震荡/不稳定
            # 推荐：
            # r=8 → 2e-4
            # r=16 → 1e-4 ~ 2e-4


            # ===== Batch控制 =====

            "batch_size": 1,
            # 每张GPU上的batch size
            # 直接影响显存占用（最敏感参数之一）

            "gradient_accumulation_steps": 8,
            # 梯度累积步数（模拟更大batch）
            # 实际batch = batch_size × accumulation
            # 这里等效 batch = 2 × 8 = 16
            # 用于在显存不足时扩大batch


            # ===== 序列长度 =====

            "max_length": 2048,
            # 最大token长度（上下文窗口）
            # ↑ length → 能处理更长文本，但显存指数增长
            # 这是显存最大消耗来源之一
            # 常用：512 / 1024 / 2048


            # ===== 日志 =====

            "logging_steps": 8,
            # 每多少step记录一次日志（loss等）
            # 太小 → 日志频繁（影响速度）
            # 太大 → 监控不及时


            # ===== 模型保存 =====

            "save_total_limit": 2,
            # 最多保留多少个checkpoint
            # 防止磁盘爆满
            # 旧的checkpoint会被自动删除


            # ===== 正则化 =====

            "weight_decay": 0.05,
            # 权重衰减（L2正则）
            # 防止模型过拟合
            # LoRA中作用较小，但建议保留


            "max_grad_norm": 0.8,
            # 梯度裁剪（gradient clipping）
            # 防止梯度爆炸
            # 常用：0.5 ~ 1.0


            # ===== 验证策略 =====

            "eval_strategy": "steps",
            # 评估策略：
            # "no" → 不评估
            # "epoch" → 每个epoch评估
            # "steps" → 每N步评估（更细粒度，推荐）

            "eval_steps": 20,
            # 每多少step进行一次验证
            # 与 evaluation_strategy="steps" 配合使用
            # 用于监控val loss变化

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
        validation_text: Optional[list] = None,
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
            training_text=training_text,
            validation_text=validation_text,
            config=config,
            on_progress=on_progress
        )

    def training_progress_true(
        self,
        task_id: str,
        training_text: Optional[str] = None,
        validation_text: Optional[list] = None,
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
        # Import here (not at module level) to avoid initializing CUDA in Celery's parent fork process
        try:
            import torch
            from transformers import (
                TrainingArguments,
                Trainer,
                TrainerCallback,
                DataCollatorForLanguageModeling,
                EarlyStoppingCallback,
            )
            from peft import (
                LoraConfig,
                get_peft_model,
                prepare_model_for_kbit_training,
            )
            from datasets import Dataset
        except ImportError as e:
            raise RuntimeError(
                "QLoRA training requires transformers, peft, and datasets. "
                "Install with: pip install transformers peft datasets accelerate bitsandbytes"
            ) from e

        if not training_text:
            raise ValueError("training_text is required for QLoRA training")

        # Merge config with defaults
        train_config = self.training_config.copy()
        if config:
            train_config.update(config)

        logger.info(f"[Training] training config: {train_config}")

        base_model = train_config.get("base_model")
        if not base_model:
            raise ValueError("base_model is required for QLoRA training")
        base_model = BASE_MODEL_MAP.get(base_model, base_model)

        start_time = time.time()
        output_dir = os.path.join(self.models_dir, str(task_id))
        os.makedirs(output_dir, exist_ok=True)

        total_epochs = train_config["num_epochs"]

        # Progress callback wrapper
        class ProgressCallback(TrainerCallback):
            def __init__(self, outer, task_id, total_epochs, start_time, on_progress):
                self.outer = outer
                self.task_id = task_id
                self.total_epochs = total_epochs
                self.start_time = start_time
                self.on_progress = on_progress
                # self.current_step = 0
                # self.total_steps = total_epochs * 10  # Approximate

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
                    grad_norm = logs.get('grad_norm')
                    lr = logs.get('learning_rate')
                    epoch = logs.get('epoch', state.epoch)
                    current_epoch = int(epoch) + 1

                    progress_data = {
                        "task_id": self.task_id,
                        "status": "PROCESSING",
                        "progress": progress,
                        "current_epoch": min(current_epoch, self.total_epochs),
                        "total_epochs": self.total_epochs,

                        "current_loss": round(loss, 4),
                        "grad_norm": round(grad_norm, 4) if grad_norm else None,
                        "learning_rate": lr,
                        "epoch": round(epoch, 3),

                        "elapsed_time": elapsed,
                        "estimated_remaining": remaining,
                        "log_lines": [
                            f"Epoch {epoch:.3f}/{self.total_epochs}",
                            f"Loss: {loss:.4f}",
                            f"Grad Norm: {grad_norm:.4f}" if grad_norm else "",
                            f"Learning Rate: {lr:.6f}" if lr else "",
                            f"Progress: {progress}%",
                            f"Elapsed: {elapsed}s",
                        ],
                    }
                    self.on_progress(progress_data)

        model = None
        try:
            # Load base model via global manager (shared with inference)
            model, tokenizer = model_manager.load_model(base_model)
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

            # Prepare model for k-bit training
            model = prepare_model_for_kbit_training(model)
            model.gradient_checkpointing_enable()
            model.config.use_cache = False

            # Configure LoRA
            lora_config = LoraConfig(
                r=train_config["lora_r"],
                lora_alpha=2*train_config["lora_r"],
                target_modules=["q_proj", "v_proj"],
                lora_dropout=train_config["lora_dropout"],
                bias="none",
                task_type="CAUSAL_LM",
            )

            model = get_peft_model(model, lora_config)

            # training_text = clean_and_filter_dataset(training_text)
            # validation_text = clean_and_filter_dataset(validation_text or [])

            # ========= Dataset =========
            train_dataset = Dataset.from_list(training_text)
            val_dataset = Dataset.from_list(validation_text or [])

            def _normalize_ids(result):
                """Normalize tokenizer output to a flat list of int token IDs."""
                if hasattr(result, "input_ids"):
                    ids = result.input_ids
                elif isinstance(result, dict) and "input_ids" in result:
                    ids = result["input_ids"]
                else:
                    ids = result
                # Convert tensor/array to list
                if hasattr(ids, "tolist"):
                    ids = ids.tolist()
                # Unwrap batch dimension if present
                if isinstance(ids, list) and len(ids) > 0 and isinstance(ids[0], list):
                    ids = ids[0]
                return list(ids)

            # ========= tokenize + label mask =========
            def tokenize_fn(example):
                messages = example["messages"]

                if not hasattr(tokenizer, "apply_chat_template"):
                    raise RuntimeError(
                        "Tokenizer does not support apply_chat_template, "
                        "which is required for chat-format training."
                    )

                # 完整 tokenize（不 truncation），用于计算 labels
                full_input_ids = _normalize_ids(tokenizer.apply_chat_template(
                    messages,
                    tokenize=True,
                    add_generation_prompt=False,
                ))
                full_labels = [-100] * len(full_input_ids)

                # 逐条计算 cumulative token lengths，确定 assistant 部分范围
                cum_lens = [0]
                for i in range(1, len(messages) + 1):
                    prefix_ids = _normalize_ids(tokenizer.apply_chat_template(
                        messages[:i],
                        tokenize=True,
                        add_generation_prompt=False,
                    ))
                    cum_lens.append(len(prefix_ids))

                # 只保留 assistant 部分的 labels
                for i, msg in enumerate(messages):
                    if msg.get("role") == "assistant":
                        start = cum_lens[i]
                        end = cum_lens[i + 1]
                        for j in range(start, end):
                            full_labels[j] = full_input_ids[j]

                # truncation 和 padding
                max_len = train_config["max_length"]
                attention_mask = [1] * len(full_input_ids)

                if len(full_input_ids) > max_len:
                    input_ids = full_input_ids[:max_len]
                    labels = full_labels[:max_len]
                    attention_mask = attention_mask[:max_len]
                else:
                    pad_len = max_len - len(full_input_ids)
                    pad_token_id = tokenizer.pad_token_id
                    input_ids = full_input_ids + [pad_token_id] * pad_len
                    labels = full_labels + [-100] * pad_len
                    attention_mask = attention_mask + [0] * pad_len

                return {
                    "input_ids": input_ids,
                    "attention_mask": attention_mask,
                    "labels": labels,
                }

            train_dataset = train_dataset.map(tokenize_fn, remove_columns=train_dataset.column_names)
            val_dataset = val_dataset.map(tokenize_fn, remove_columns=val_dataset.column_names)

            # ========= collator =========
            data_collator = DataCollatorForLanguageModeling(
                tokenizer=tokenizer,
                mlm=False,
                pad_to_multiple_of=8
            )

            # ========= 训练参数 =========
            train_samples = len(train_dataset)
            effective_batch_size = train_config["batch_size"] * train_config["gradient_accumulation_steps"]
            steps_per_epoch = max(1, train_samples // effective_batch_size)
            total_steps = steps_per_epoch * total_epochs
            warmup_steps = int(total_steps * 0.05)

            args = TrainingArguments(
                output_dir=output_dir,
                num_train_epochs=train_config["num_epochs"],
                per_device_train_batch_size=train_config["batch_size"],
                gradient_accumulation_steps=train_config["gradient_accumulation_steps"],

                learning_rate=train_config["learning_rate"],
                lr_scheduler_type="cosine",
                warmup_steps=warmup_steps,

                logging_steps=train_config["logging_steps"],
                logging_strategy="steps",

                save_strategy="best",
                save_total_limit=train_config["save_total_limit"],

                bf16=True,
                fp16=False,

                weight_decay=train_config["weight_decay"],
                max_grad_norm=train_config["max_grad_norm"],

                eval_strategy=train_config["eval_strategy"],
                eval_steps=train_config["eval_steps"],

                metric_for_best_model="eval_loss",
                load_best_model_at_end=True,
                greater_is_better=False,

                report_to=[],
            )

            # ========= Trainer =========
            callbacks = [
                ProgressCallback(self, task_id, total_epochs, start_time, on_progress),
            ]
            if len(val_dataset) > 0:
                callbacks.append(EarlyStoppingCallback(early_stopping_patience=2))

            trainer = Trainer(
                model=model,
                args=args,
                train_dataset=train_dataset,
                eval_dataset=val_dataset if len(val_dataset) > 0 else None,
                data_collator=data_collator,
                callbacks=callbacks,
            )

            trainer.train()

            # Save final adapter
            model.save_pretrained(output_dir)
            tokenizer.save_pretrained(output_dir)

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

            return output_dir

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

        # Generate adapter files and return path
        adapter_dir = self.generate_adapter_file(task_id, task_id)
        return adapter_dir


# Global training service instance
training_service = TrainingService()
