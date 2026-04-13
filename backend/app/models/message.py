"""Message model for style transfer history."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

if TYPE_CHECKING:
    from .style import Style


class Message(Base):
    """Message model representing a chat history entry."""

    __tablename__ = "messages"

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
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="角色: user/assistant/system"
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="消息内容"
    )
    original_text: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="原文内容（用于风格转换记录）"
    )
    requirement: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="用户需求（用于风格转换记录）"
    )
    meta_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="额外元数据"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    # Relationships
    style: Mapped["Style"] = relationship(
        "Style",
        back_populates="messages",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, style_id={self.style_id}, role={self.role})>"
