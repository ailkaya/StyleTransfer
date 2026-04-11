"""Common schemas for API responses."""

from typing import Generic, TypeVar, Optional
from pydantic import BaseModel
from datetime import datetime

T = TypeVar("T")


class Response(BaseModel, Generic[T]):
    """Standard API response wrapper."""

    code: int = 200
    message: str = "success"
    data: Optional[T] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = 1
    page_size: int = 10

    class Config:
        from_attributes = True


class PaginationInfo(BaseModel):
    """Pagination information."""

    total: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    items: list[T]
    pagination: PaginationInfo

    class Config:
        from_attributes = True
