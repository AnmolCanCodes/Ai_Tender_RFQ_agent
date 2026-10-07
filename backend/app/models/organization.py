from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.core.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    tenders = relationship("Tender", back_populates="organization", cascade="all, delete-orphan")
    company_profile = relationship("CompanyProfile", back_populates="organization", uselist=False, cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="organization", cascade="all, delete-orphan")