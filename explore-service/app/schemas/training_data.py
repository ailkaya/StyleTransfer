"""Schemas for TrainingData model."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class TrainingDataBase(BaseModel):
    """Base schema for TrainingData."""

    title: str = Field(..., min_length=1, max_length=100, description="Title")
    description: Optional[str] = Field(None, max_length=2000, description="Description")


class TrainingDataCreate(TrainingDataBase):
    """Schema for creating a new training data upload."""

    pass


class TrainingDataUpdate(BaseModel):
    """Schema for updating training data metadata."""

    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)


class TrainingDataInDB(TrainingDataBase):
    """Schema for TrainingData as stored in database."""

    id: str
    file_path: str
    file_size: int
    file_name: str
    uploader_id: str
    uploader_name: str
    upload_time: datetime
    download_count: int
    is_active: bool

    model_config = {"from_attributes": True}

    @field_validator("id", "uploader_id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class TrainingDataResponse(TrainingDataInDB):
    """Schema for TrainingData API response."""

    pass


class TrainingDataListItem(BaseModel):
    """Schema for TrainingData list item (lightweight)."""

    id: str
    title: str
    description: Optional[str] = None
    file_size: int
    file_name: str
    uploader_id: str
    uploader_name: str
    upload_time: datetime
    download_count: int
    is_active: bool

    model_config = {"from_attributes": True}

    @field_validator("id", "uploader_id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class TrainingDataSearchParams(BaseModel):
    """Schema for training data search parameters."""

    search: Optional[str] = Field(None, description="Search keyword")
    sort_by: str = Field("upload_time", description="Sort field")
    sort_order: str = Field("desc", description="Sort direction")
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v: str) -> str:
        allowed = {"upload_time", "download_count", "title"}
        if v not in allowed:
            raise ValueError(f"sort_by must be one of {allowed}")
        return v

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v: str) -> str:
        v = v.lower()
        if v not in ("asc", "desc"):
            raise ValueError("sort_order must be 'asc' or 'desc'")
        return v


class TrainingDataPreviewResponse(BaseModel):
    """Schema for training data preview response."""

    id: str
    title: str
    total_lines: int
    preview_lines: list[str]
    has_more: bool
