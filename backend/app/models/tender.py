from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Tender(Base):
    __tablename__ = "tenders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    reference_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    issuing_organization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_value: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    emd_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    submission_deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    pre_bid_meeting_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    clarification_deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="tenders")
    documents = relationship("Document", back_populates="tender", cascade="all, delete-orphan")
    requirements = relationship("Requirement", back_populates="tender", cascade="all, delete-orphan")
    chunks = relationship("Chunk", back_populates="tender", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="tender")


