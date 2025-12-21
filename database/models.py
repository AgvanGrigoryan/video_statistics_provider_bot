from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base
from database.mixins import MetricsCountMixin, TimestampMixin


class VideoModel(Base, TimestampMixin, MetricsCountMixin):
    """ORM model for videos table.

    Stores statistics on the video.

    """
    __tablename__ = "videos"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, nullable=False)
    creator_id: Mapped[str] = mapped_column(String, nullable=False)
    video_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        Index(None, "creator_id"),
        Index(None, "video_created_at"),
        Index(None, "views_count"),
    )

 
class VideoSnapshotModel(Base, TimestampMixin, MetricsCountMixin):
    """ORM model for video_snapshots tables
    
    Stores hourly snapshots of video statistics with current values and deltas.
    
    """

    __tablename__ = "video_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True, nullable=False)
    video_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    delta_views_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delta_likes_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delta_comments_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delta_reports_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index(None, "created_at"),
        Index(None, "video_id"),
        Index(None, "delta_views_count"),
    )