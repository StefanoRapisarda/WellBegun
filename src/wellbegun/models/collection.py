from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from wellbegun.models.base import Base
from wellbegun.models.entity import Entity


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    member_entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    statuses: Mapped[list["CategoryStatus"]] = relationship(
        "CategoryStatus", back_populates="category", cascade="all, delete-orphan",
        order_by="CategoryStatus.position",
    )
    collections: Mapped[list["Collection"]] = relationship(
        "Collection", back_populates="category",
    )


class CategoryStatus(Base):
    __tablename__ = "category_statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=False
    )
    value: Mapped[str] = mapped_column(String(50), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    category: Mapped["Category"] = relationship("Category", back_populates="statuses")

    __table_args__ = (
        UniqueConstraint("category_id", "value"),
    )


class Collection(Entity):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(
        Integer, ForeignKey("entities.id"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=False
    )

    category: Mapped["Category"] = relationship("Category", back_populates="collections")
    items: Mapped[list["CollectionItem"]] = relationship(
        "CollectionItem", back_populates="collection", cascade="all, delete-orphan",
        order_by="CollectionItem.position",
    )

    __mapper_args__ = {
        "polymorphic_identity": "collection",
    }


class CollectionItem(Base):
    __tablename__ = "collection_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    collection_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("entities.id"), nullable=False
    )
    member_entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    member_entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    header: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    collection: Mapped["Collection"] = relationship(
        "Collection", back_populates="items"
    )

    __table_args__ = (
        UniqueConstraint("collection_id", "member_entity_type", "member_entity_id"),
    )
