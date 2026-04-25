"""Adapter model for shared LoRA adapters."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, BigInteger, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Adapter(Base):
    """Adapter model representing a shared LoRA adapter."""

    __tablename__ = "adapters"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    style_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Style name"
    )
    style_tag: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Style tag for categorization"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Style description"
    )
    base_model: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Base model identifier"
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Stored file path"
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        comment="File size in bytes"
    )
    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original file name"
    )
    local_style_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
        comment="Local backend style ID (UUID) to prevent duplicate uploads"
    )
    uploader_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploader_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Uploader display name (denormalized)"
    )
    upload_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )
    download_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total download count"
    )
    weekly_download_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Weekly download count"
    )
    evaluation_results: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Evaluation results JSON"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    uploader: Mapped["User"] = relationship(
        "User",
        back_populates="adapters",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Adapter(id={self.id}, style_name={self.style_name})>"
