from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from log_input_panels.models.base import Base


class LearningTrack(Base):
    __tablename__ = "learning_tracks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    items: Mapped[list["LearningTrackItem"]] = relationship(
        "LearningTrackItem", back_populates="learning_track", cascade="all, delete-orphan"
    )
    goals: Mapped[list["LearningGoal"]] = relationship(
        "LearningGoal", back_populates="learning_track", cascade="all, delete-orphan"
    )


class LearningTrackItem(Base):
    __tablename__ = "learning_track_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    learning_track_id: Mapped[int] = mapped_column(Integer, ForeignKey("learning_tracks.id"), nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("sources.id"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="not_started", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    learning_track: Mapped["LearningTrack"] = relationship(
        "LearningTrack", back_populates="items"
    )

    __table_args__ = (
        UniqueConstraint("learning_track_id", "source_id"),
    )


class LearningGoal(Base):
    __tablename__ = "learning_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    learning_track_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("learning_tracks.id"), nullable=False
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    learning_track: Mapped["LearningTrack"] = relationship(
        "LearningTrack", back_populates="goals"
    )
