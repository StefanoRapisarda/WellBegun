from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from wellbegun.models.base import Base


class ReadingList(Base):
    __tablename__ = "reading_lists"

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

    items: Mapped[list["ReadingListItem"]] = relationship(
        "ReadingListItem", back_populates="reading_list", cascade="all, delete-orphan"
    )


class ReadingListItem(Base):
    __tablename__ = "reading_list_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reading_list_id: Mapped[int] = mapped_column(Integer, ForeignKey("reading_lists.id"), nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("sources.id"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="unread", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    reading_list: Mapped["ReadingList"] = relationship(
        "ReadingList", back_populates="items"
    )

    __table_args__ = (
        UniqueConstraint("reading_list_id", "source_id"),
    )
