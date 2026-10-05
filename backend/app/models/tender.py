from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Numeric ,Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

class Tender(Base):
    __tablename__ = "tenders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    organisation_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    reference_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    issuing_organization: Mapped[str] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    estimated_value: Mapped[float]= mapped_column(Numeric(15, 2), nullable=False)
    submission_deadline: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    status: Mapped[str]= mapped_column(String(30), nullable=False, default="DRAFT")
    created_at: Mapped[datetime]= mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime]= mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("Document", back_populates="tender")
    organization = relationship("Organization", back_populates="tenders")
    requirements = relationship("Requirement", back_populates="tender")

