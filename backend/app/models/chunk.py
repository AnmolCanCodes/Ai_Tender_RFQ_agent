from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"),
        nullable=False,
        index=True)
    tender_id: Mapped[int] = mapped_column(ForeignKey("documents.id"),
        nullable=False,
        index=True)
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    section: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    # Replace 384 with the dimension
    # of your actual embedding model.
    embedding = mapped_column(
        Vector(384),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    document = relationship(
        "Document",
        back_populates="chunks"
    )