"""Schemas for configuration management."""

from typing import Optional, List, Any, Literal
from pydantic import BaseModel, Field


class ConfigItem(BaseModel):
    """Single configuration item schema."""
    key: str = Field(..., description="Configuration key name")
    value: str = Field(..., description="Configuration value (may be masked for sensitive fields)")
    raw_value: Optional[str] = Field(None, description="Raw value before masking (only for display)")
    value_type: Literal["string", "boolean", "integer", "float", "secret"] = Field(
        "string", description="Type of the configuration value"
    )
    category: str = Field(..., description="Category of the configuration")
    description: str = Field("", description="Description of the configuration")
    is_sensitive: bool = Field(False, description="Whether this field contains sensitive data")
    requires_restart: bool = Field(False, description="Whether changing this requires service restart")
    is_modified: bool = Field(False, description="Whether this item has been modified (frontend use)")


class ConfigCategory(BaseModel):
    """Configuration category with items."""
    name: str = Field(..., description="Category name")
    label: str = Field(..., description="Display label for the category")
    items: List[ConfigItem] = Field(default_factory=list, description="Configuration items in this category")


class ConfigListResponse(BaseModel):
    """Response schema for listing configurations."""
    categories: List[ConfigCategory] = Field(default_factory=list, description="Configuration categories")
    env_path: str = Field(..., description="Path to the .env file")


class ConfigUpdateItem(BaseModel):
    """Single configuration item for update."""
    key: str = Field(..., description="Configuration key name")
    value: str = Field(..., description="New configuration value")


class ConfigUpdateRequest(BaseModel):
    """Request schema for updating configurations."""
    configs: List[ConfigUpdateItem] = Field(..., description="List of configurations to update")


class ConfigUpdateResponse(BaseModel):
    """Response schema for configuration update."""
    updated: List[str] = Field(default_factory=list, description="List of successfully updated keys")
    failed: List[dict] = Field(default_factory=list, description="List of failed updates with reasons")
    backup_path: Optional[str] = Field(None, description="Path to the backup file")
