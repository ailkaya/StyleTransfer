"""Schemas for Style model."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class StyleBase(BaseModel):
    """Base schema for Style."""

    name: str = Field(..., min_length=2, max_length=50, description="风格名称")
    description: Optional[str] = Field(None, max_length=500, description="风格描述")
    target_style: str = Field(..., min_length=1, max_length=50, description="目标风格类型")


class StyleCreate(StyleBase):
    """Schema for creating a new style."""

    base_model: str = Field(default="llama-2-3b", description="底座模型标识")


class StyleUpdate(BaseModel):
    """Schema for updating a style."""

    name: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    target_style: Optional[str] = Field(None, min_length=1, max_length=50)


class StyleInDB(StyleBase):
    """Schema for Style as stored in database."""

    id: str
    base_model: str
    adapter_path: Optional[str] = None
    status: str
    source: str = "local"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class StyleResponse(StyleInDB):
    """Schema for Style API response."""

    pass


class StyleListItem(BaseModel):
    """Schema for Style list item."""

    id: str
    name: str
    description: Optional[str] = None
    target_style: str
    base_model: str = "llama-2-3b"
    status: str
    source: str = "local"
    task_status: Optional[str] = None  # Latest task status
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class BaseModelInfo(BaseModel):
    """Schema for available base model metadata."""

    id: str
    name: str
    type: str
    description: str
    params: str
    speed: str
    speed_value: int = 0
