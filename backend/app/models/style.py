"""Style model for text style transfer."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

if TYPE_CHECKING:
    from .task import Task
    from .message import Message
    from .evaluation import Evaluation


class Style(Base):
    """Style model representing a text style configuration."""

    __tablename__ = "styles"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="风格名称，2-50字符"
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="风格描述，最大500字符"
    )
    target_style: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="目标风格类型，如幽默、学术等"
    )
    base_model: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="llama-2-3b",
        comment="底座模型标识，如llama-2-3b, Qwen3-1.7B"
    )
    adapter_path: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        comment="Adapter路径（训练后填充）"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="状态: pending/preprocessing/training/completed/failed/available/evaluating"
    )
    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="local",
        comment="来源: local(本地训练) / explored(从探索拉取)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="style",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="style",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    evaluations: Mapped[list["Evaluation"]] = relationship(
        "Evaluation",
        back_populates="style",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Style(id={self.id}, name={self.name}, status={self.status})>"
