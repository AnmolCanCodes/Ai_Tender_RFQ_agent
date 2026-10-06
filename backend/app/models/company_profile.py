from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=False,
        unique=True
    )

    legal_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    annual_turnover: Mapped[float | None] = mapped_column(
        Numeric(15, 2),
        nullable=True
    )

    years_experience: Mapped[int | None] = mapped_column(
        nullable=True
    )

    gst_number: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True
    )

    website: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )