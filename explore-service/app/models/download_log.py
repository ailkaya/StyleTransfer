"""DownloadLog model for tracking weekly downloads."""

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DownloadLog(Base):
    """DownloadLog model for tracking resource downloads."""

    __tablename__ = "download_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    resource_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Downloaded resource ID"
    )
    resource_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Resource type: adapter / training_data"
    )
    downloaded_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<DownloadLog(id={self.id}, resource_id={self.resource_id}, type={self.resource_type})>"
