"""Schemas for Message model."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class ChatMessage(BaseModel):
    """Schema for a chat message in history."""

    role: str = Field(..., description="角色: user/assistant/system")
    content: str = Field(..., description="消息内容")


class MessageCreate(BaseModel):
    """Schema for creating a new message (style transfer request)."""

    original_text: str = Field(..., min_length=1, description="原文内容")
    requirement: str = Field(..., min_length=1, description="转换需求")
    history: Optional[List[ChatMessage]] = Field(default=None, description="历史对话")


class MessageResponse(BaseModel):
    """Schema for message response."""

    id: str
    style_id: str
    role: str
    content: str
    original_text: Optional[str] = None
    requirement: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("id", "style_id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class MessageListItem(BaseModel):
    """Schema for message list item."""

    id: str
    role: str
    content_preview: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class StyleTransferRequest(BaseModel):
    """Schema for style transfer request."""

    original_text: str = Field(..., description="原文内容")
    requirement: str = Field(..., description="转换需求")
    style_id: str = Field(..., description="目标风格ID")


class StyleTransferResponse(BaseModel):
    """Schema for style transfer response."""

    message: MessageResponse
    style_name: str
