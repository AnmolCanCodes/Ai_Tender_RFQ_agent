from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Requirement(Base):
    __tablename__ = "requirements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tender_id: Mapped[int] = mapped_column(ForeignKey("tenders.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )

    title: Mapped[str] = mapped_column(
        String(300),
        nullable=False
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    source_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id"),
        nullable=True
    )

    source_page: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    source_section: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    mandatory: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    # Verification status: PENDING, VERIFIED, REJECTED
    status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        nullable=False
    )

    # Capability Match status: PENDING, MATCHED, PARTIAL, MISSING, REQUIRES_VERIFICATION
    match_status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        nullable=False
    )

    matched_evidence: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    verification_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    is_checklist_item: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    checklist_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    checklist_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    tender = relationship(
        "Tender",
        back_populates="requirements"
    )