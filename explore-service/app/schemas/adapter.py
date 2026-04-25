"""Schemas for Adapter model."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class EvaluationResults(BaseModel):
    """Schema for evaluation results."""

    overall_score: float = 0.0
    sample_count: int = 0
    char_retention: float = 0.0
    style_score: float = 0.0
    fluency_score: float = 0.0
    vocab_diversity: float = 0.0
    length_ratio: float = 0.0
    bleu_score: float = 0.0
    bert_score: float = 0.0
    avg_response_time: float = 0.0
    samples: list[dict] = []
    comment: Optional[str] = None


class AdapterBase(BaseModel):
    """Base schema for Adapter."""

    style_name: str = Field(..., min_length=1, max_length=100, description="Style name")
    style_tag: str = Field(..., min_length=1, max_length=50, description="Style tag")
    description: Optional[str] = Field(None, max_length=2000, description="Description")
    base_model: str = Field(..., min_length=1, max_length=50, description="Base model")


class AdapterCreate(AdapterBase):
    """Schema for creating a new adapter upload."""

    evaluation_results: Optional[EvaluationResults] = Field(None, description="Evaluation results")


class AdapterUpdate(BaseModel):
    """Schema for updating adapter metadata."""

    style_name: Optional[str] = Field(None, min_length=1, max_length=100)
    style_tag: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=2000)
    base_model: Optional[str] = Field(None, min_length=1, max_length=50)


class AdapterInDB(AdapterBase):
    """Schema for Adapter as stored in database."""

    id: str
    file_path: str
    file_size: int
    file_name: str
    local_style_id: Optional[str] = None
    uploader_id: str
    uploader_name: str
    upload_time: datetime
    download_count: int
    weekly_download_count: int
    evaluation_results: Optional[dict] = None
    is_active: bool

    model_config = {"from_attributes": True}

    @field_validator("id", "uploader_id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class AdapterResponse(AdapterInDB):
    """Schema for Adapter API response."""

    pass


class AdapterListItem(BaseModel):
    """Schema for Adapter list item (lightweight)."""

    id: str
    style_name: str
    style_tag: str
    description: Optional[str] = None
    base_model: str
    file_size: int
    file_name: str
    local_style_id: Optional[str] = None
    uploader_id: str
    uploader_name: str
    upload_time: datetime
    download_count: int
    weekly_download_count: int
    overall_score: Optional[float] = None
    evaluation_results: Optional[dict] = None
    is_active: bool

    model_config = {"from_attributes": True}

    @field_validator("id", "uploader_id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class AdapterSearchParams(BaseModel):
    """Schema for adapter search parameters."""

    search: Optional[str] = Field(None, description="Search keyword")
    style_tag: Optional[str] = Field(None, description="Filter by tag")
    base_model: Optional[str] = Field(None, description="Filter by base model")
    sort_by: str = Field("upload_time", description="Sort field")
    sort_order: str = Field("desc", description="Sort direction")
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v: str) -> str:
        allowed = {"upload_time", "download_count", "weekly_download_count", "style_name"}
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
