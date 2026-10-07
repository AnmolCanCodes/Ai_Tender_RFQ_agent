from datetime import datetime
from pydantic import BaseModel


class CompanyProfileCreate(BaseModel):
    legal_name: str
    annual_turnover: float | None = None
    years_experience: int | None = None
    gst_number: str | None = None
    website: str | None = None
    certifications: str | None = None
    technical_capabilities: str | None = None
    past_contracts_count: int | None = None
    past_experience_summary: str | None = None
    description: str | None = None


class CompanyProfileResponse(BaseModel):
    id: int
    legal_name: str
    annual_turnover: float | None = None
    years_experience: int | None = None
    gst_number: str | None = None
    website: str | None = None
    certifications: str | None = None
    technical_capabilities: str | None = None
    past_contracts_count: int | None = None
    past_experience_summary: str | None = None
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }