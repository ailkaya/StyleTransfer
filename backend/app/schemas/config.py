"""Schemas for Config model."""

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class LLMConfig(BaseModel):
    """Schema for LLM API configuration."""

    model_config = ConfigDict(protected_namespaces=(), from_attributes=True)

    base_url: str = Field(..., description="API基础URL")
    model_name: str = Field(..., description="模型名称")
    api_key: str = Field(..., description="API密钥")


class LLMConfigResponse(BaseModel):
    """Schema for LLM config response (without api_key)."""

    model_config = ConfigDict(protected_namespaces=(), from_attributes=True)

    base_url: str = Field(..., description="API基础URL")
    model_name: str = Field(..., description="模型名称")
    has_api_key: bool = Field(default=False, description="是否已配置API密钥")


class ConfigInDB(BaseModel):
    """Schema for Config as stored in database."""

    key: str
    value: str
    description: str
    updated_at: datetime

    class Config:
        from_attributes = True


class ConfigUpdate(BaseModel):
    """Schema for updating config."""

    key: str = Field(..., description="配置键")
    value: str = Field(..., description="配置值")
    description: str = Field(default="", description="配置说明")
