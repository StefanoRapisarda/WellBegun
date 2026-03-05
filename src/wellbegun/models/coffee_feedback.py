"""Coffee Table chat feedback — stores user ratings of multi-option responses."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from wellbegun.models.base import Base


class CoffeeFeedback(Base):
    __tablename__ = "coffee_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    original_message: Mapped[str] = mapped_column(Text, nullable=False)
    conversation_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    option_1: Mapped[str] = mapped_column(Text, nullable=False)
    option_2: Mapped[str] = mapped_column(Text, nullable=False)
    option_3: Mapped[str] = mapped_column(Text, nullable=False)
    option_1_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    option_2_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    option_3_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    chosen_option: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ideal_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
