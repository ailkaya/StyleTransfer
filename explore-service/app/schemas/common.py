"""Common schemas for API responses."""

from typing import Generic, TypeVar, Optional
from pydantic import BaseModel, field_validator
from datetime import datetime

T = TypeVar("T")


class PaginationInfo(BaseModel):
    """Pagination information."""

    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    items: list[T]
    pagination: PaginationInfo
