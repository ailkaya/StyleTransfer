"""Evaluation model for storing style model evaluation results."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Float, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

if TYPE_CHECKING:
    from .task import Task
    from .style import Style


class Evaluation(Base):
    """Evaluation model representing model evaluation results."""

    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    task_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="外键 -> Task.id"
    )
    style_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("styles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="外键 -> Style.id"
    )

    # Basic info
    task_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="",
        comment="任务名称"
    )
    target_style: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="",
        comment="目标风格"
    )

    # Overall metrics
    overall_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="综合评分"
    )
    sample_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="样本数量"
    )

    # Detailed metrics
    # semantic_score: Mapped[float] = mapped_column(
    #     Float,
    #     nullable=False,
    #     default=0.0,
    #     comment="语义保留率"
    # )
    char_retention: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="字符保留率"
    )
    style_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="风格符合度"
    )
    fluency_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="文本流畅度"
    )
    vocab_diversity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="词汇多样性"
    )
    length_ratio: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="长度变化率"
    )
    bleu_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="BLEU得分"
    )
    avg_response_time: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="平均响应时间(秒)"
    )

    # Sample data (stored as JSON string for simplicity)
    samples: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="样本对比数据(JSON格式)"
    )

    # User comment/review
    comment: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="用户评价/反馈"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="创建时间"
    )

    # Relationships
    task: Mapped["Task"] = relationship(
        "Task",
        back_populates="evaluation",
        lazy="selectin"
    )
    style: Mapped["Style"] = relationship(
        "Style",
        back_populates="evaluations",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Evaluation(id={self.id}, task_id={self.task_id}, overall_score={self.overall_score})>"

    def to_dict(self) -> dict:
        """Convert evaluation to dictionary format for API response."""
        import json
        return {
            "task_id": str(self.task_id),
            "task_name": self.task_name,
            "target_style": self.target_style,
            "generated_at": self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else "-",
            "overall_score": self.overall_score,
            "sample_count": self.sample_count,
            # "semantic_score": self.semantic_score,
            "char_retention": self.char_retention,
            "style_score": self.style_score,
            "fluency_score": self.fluency_score,
            "vocab_diversity": self.vocab_diversity,
            "length_ratio": self.length_ratio,
            "bleu_score": self.bleu_score,
            "avg_response_time": self.avg_response_time,
            "samples": json.loads(self.samples) if self.samples else [],
            "comment": self.comment
        }
