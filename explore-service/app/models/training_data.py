"""TrainingData model for shared training text files."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, BigInteger, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class TrainingData(Base):
    """TrainingData model representing shared training text files."""

    __tablename__ = "training_data"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Title"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Description"
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
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    uploader: Mapped["User"] = relationship(
        "User",
        back_populates="training_data_items",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<TrainingData(id={self.id}, title={self.title})>"
