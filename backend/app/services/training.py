"""Training service for style model fine-tuning.

This module contains placeholder implementation for v0.1.
In v0.2+, it will implement actual QLoRA training logic.
"""

import os
import time
import random
from datetime import datetime
from typing import Optional


class TrainingService:
    """Service for managing style model training."""

    def __init__(self):
        self.models_dir = os.path.join(os.getcwd(), "models", "adapters")
        os.makedirs(self.models_dir, exist_ok=True)

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

    def simulate_training_progress(
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
                time.sleep(0.5)  # Simulate work

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
