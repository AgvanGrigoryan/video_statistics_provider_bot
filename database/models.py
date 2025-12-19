from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
)
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base
from database.mixins import MetricsCountMixin, TimestampMixin


class VideoModel(Base, TimestampMixin, MetricsCountMixin):
    """ORM model for videos table.

    Stores statistics on the video.

    """
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    creator_id: Mapped[int] = mapped_column(Integer, nullable=False)
    video_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

 
class VideoSnapshotModel(Base, TimestampMixin, MetricsCountMixin):
    """ORM model for video_snapshots tables
    
    Stores hourly snapshots of video statistics with current values and deltas.
    
    """

    __tablename__ = "video_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    delta_views_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delta_likes_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delta_comments_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delta_reports_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
