"""Task model for training jobs."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

if TYPE_CHECKING:
    from .style import Style
    from .evaluation import Evaluation


class Task(Base):
    """Task model representing a training job."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    style_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("styles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="外键 -> Style.id"
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="",
        comment="任务名称（对应风格名称）"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        index=True,
        comment="状态: PENDING/PROCESSING/COMPLETED/FAILED/EVALUATING"
    )
    progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="进度百分比 0-100"
    )
    config: Mapped[dict] = mapped_column(
        JSON,
        nullable=True,
        comment="训练配置参数"
    )
    logs: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="训练日志"
    )
    result_path: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        comment="输出模型路径"
    )
    training_data_path: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        comment="训练数据文件路径"
    )
    error_message: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息（失败时）"
    )
    current_epoch: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
        comment="当前epoch"
    )
    total_epochs: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
        comment="总epoch数"
    )
    current_loss: Mapped[float] = mapped_column(
        JSON,
        nullable=True,
        comment="当前loss值"
    )
    elapsed_time: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
        comment="已用时间（秒）"
    )
    estimated_remaining: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
        comment="预计剩余时间（秒）"
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
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="完成时间"
    )

    # Relationships
    style: Mapped["Style"] = relationship(
        "Style",
        back_populates="tasks",
        lazy="selectin"
    )
    evaluation: Mapped[Optional["Evaluation"]] = relationship(
        "Evaluation",
        back_populates="task",
        lazy="selectin",
        uselist=False
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, style_id={self.style_id}, status={self.status}, progress={self.progress})>"
