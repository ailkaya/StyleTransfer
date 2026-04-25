"""File storage service for handling uploads and downloads."""

import os
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import settings


class FileStorageService:
    """Service for managing file storage operations."""

    def __init__(self):
        self.adapters_dir = settings.adapters_dir
        self.training_data_dir = settings.training_data_dir
        self.max_upload_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

        os.makedirs(self.adapters_dir, exist_ok=True)
        os.makedirs(self.training_data_dir, exist_ok=True)

    def _generate_unique_filename(self, original_filename: str) -> str:
        """Generate a unique filename with preserved extension."""
        ext = Path(original_filename).suffix
        unique_name = f"{uuid.uuid4().hex}{ext}"
        return unique_name

    def _validate_file_size(self, file_size: int) -> None:
        """Validate file size against max limit."""
        if file_size > self.max_upload_size:
            max_mb = settings.MAX_UPLOAD_SIZE_MB
            raise ValueError(f"File size exceeds maximum allowed size of {max_mb}MB")

    async def save_adapter_file(
        self,
        file: UploadFile,
        uploader_id: str,
        record_id: str,
    ) -> tuple[str, int, str]:
        """Save an adapter upload file. Returns (file_path, file_size, stored_filename)."""
        content = await file.read()
        file_size = len(content)

        self._validate_file_size(file_size)

        ext = Path(file.filename or "adapter.zip").suffix
        stored_filename = f"{record_id}{ext}"
        uploader_dir = os.path.join(self.adapters_dir, str(uploader_id))
        os.makedirs(uploader_dir, exist_ok=True)

        file_path = os.path.join(uploader_dir, stored_filename)

        with open(file_path, "wb") as f:
            f.write(content)

        return file_path, file_size, stored_filename

    async def save_training_data_file(
        self,
        file: UploadFile,
        uploader_id: str,
        record_id: str,
    ) -> tuple[str, int, str]:
        """Save a training data upload file. Returns (file_path, file_size, stored_filename)."""
        content = await file.read()
        file_size = len(content)

        self._validate_file_size(file_size)

        ext = Path(file.filename or "training_data.txt").suffix
        stored_filename = f"{record_id}{ext}"
        uploader_dir = os.path.join(self.training_data_dir, str(uploader_id))
        os.makedirs(uploader_dir, exist_ok=True)

        file_path = os.path.join(uploader_dir, stored_filename)

        with open(file_path, "wb") as f:
            f.write(content)

        return file_path, file_size, stored_filename

    def delete_file(self, file_path: str) -> bool:
        """Delete a file from storage."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                parent_dir = os.path.dirname(file_path)
                if os.path.isdir(parent_dir) and not os.listdir(parent_dir):
                    os.rmdir(parent_dir)
                return True
            return False
        except Exception:
            return False

    def file_exists(self, file_path: str) -> bool:
        """Check if file exists."""
        return os.path.exists(file_path)


file_storage = FileStorageService()
