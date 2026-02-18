from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from wellbegun.models.base import Base


class CustomPredicate(Base):
    __tablename__ = "custom_predicates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    forward: Mapped[str] = mapped_column(String(255), nullable=False)
    reverse: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="Custom")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
