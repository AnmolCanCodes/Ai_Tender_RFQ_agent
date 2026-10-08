from pydantic import BaseModel


class CompanyProfileCreate(BaseModel):
    legal_name: str
    annual_turnover: float | None = None
    years_experience: int | None = None
    gst_number: str | None = None
    website: str | None = None
    description: str | None = None


class CompanyProfileResponse(BaseModel):
    id: int
    legal_name: str
    annual_turnover: float | None
    years_experience: int | None
    gst_number: str | None
    website: str | None
    description: str | None

    model_config = {
        "from_attributes": True
    }