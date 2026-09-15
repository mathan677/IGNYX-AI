from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from database import Base


class Memory(Base):
    __tablename__ = "memories"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_key = Column(
        String(100),
        nullable=False,
        default="default_user",
        index=True,
    )

    category = Column(
        String(50),
        nullable=False,
        default="general",
        index=True,
    )

    key = Column(
        String(150),
        nullable=False,
        index=True,
    )

    value = Column(
        Text,
        nullable=False,
    )

    importance = Column(
        Float,
        nullable=False,
        default=0.5,
    )

    # =========================================================
    # SEMANTIC EMBEDDING
    #
    # Stored as JSON text in SQLite.
    # Example:
    # "[0.0123, -0.0456, 0.0789, ...]"
    # =========================================================

    embedding = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return (
            f"<Memory("
            f"id={self.id}, "
            f"category={self.category!r}, "
            f"value={self.value!r}"
            f")>"
        )