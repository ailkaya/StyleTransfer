"""Schemas for Task model."""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class TrainingConfig(BaseModel):
    """Training configuration schema."""

    learning_rate: float = Field(default=0.0002, description="学习率")
    num_epochs: int = Field(default=3, ge=1, le=10, description="训练轮数")
    batch_size: int = Field(default=4, ge=1, le=16, description="批次大小")
    max_length: int = Field(default=512, ge=128, le=2048, description="最大序列长度")


class TaskCreate(BaseModel):
    """Schema for creating a new training task."""

    style_id: str = Field(..., description="风格ID")
    base_model: str = Field(default="llama-2-3b", description="底座模型")
    training_text: str = Field(..., min_length=100, description="训练文本内容")
    config: TrainingConfig = Field(default_factory=TrainingConfig, description="训练配置")


class TaskInDB(BaseModel):
    """Schema for Task as stored in database."""

    id: str
    style_id: str
    status: str
    progress: int
    config: Optional[Dict[str, Any]] = None
    logs: Optional[str] = None
    result_path: Optional[str] = None
    error_message: Optional[str] = None
    current_epoch: Optional[int] = None
    total_epochs: Optional[int] = None
    current_loss: Optional[float] = None
    elapsed_time: Optional[int] = None
    estimated_remaining: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_validator("id", "style_id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class TaskResponse(TaskInDB):
    """Schema for Task API response."""

    pass


class TaskListItem(BaseModel):
    """Schema for Task list item."""

    id: str
    style_id: str
    status: str
    progress: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("id", "style_id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class TaskProgressUpdate(BaseModel):
    """Schema for task progress update via WebSocket."""

    type: str = "progress"
    data: Dict[str, Any]
    timestamp: datetime


class TaskLogsResponse(BaseModel):
    """Schema for task logs response."""

    task_id: str
    logs: str
    lines: int
