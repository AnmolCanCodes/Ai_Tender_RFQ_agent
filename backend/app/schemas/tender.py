from datetime import datetime
from pydantic import BaseModel, model_validator


class TenderCreate(BaseModel):
    title: str
    reference_number: str | None = None
    issuing_organization: str | None = None
    issuing_organistaion: str | None = None
    description: str | None = None
    estimated_value: float | None = None
    emd_amount: float | None = None
    submission_deadline: datetime | None = None
    pre_bid_meeting_date: datetime | None = None
    clarification_deadline: datetime | None = None

    @model_validator(mode="after")
    def resolve_issuing_org(self) -> "TenderCreate":
        org = self.issuing_organization or self.issuing_organistaion
        self.issuing_organization = org.strip() if org else None
        return self


class TenderUpdate(BaseModel):
    title: str | None = None
    reference_number: str | None = None
    issuing_organization: str | None = None
    description: str | None = None
    estimated_value: float | None = None
    emd_amount: float | None = None
    submission_deadline: datetime | None = None
    pre_bid_meeting_date: datetime | None = None
    clarification_deadline: datetime | None = None
    status: str | None = None


class TenderResponse(BaseModel):
    id: int
    title: str
    reference_number: str
    issuing_organization: str | None
    description: str | None
    estimated_value: float | None
    emd_amount: float | None
    submission_deadline: datetime | None
    pre_bid_meeting_date: datetime | None
    clarification_deadline: datetime | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class TenderListResponse(BaseModel):
    items: list[TenderResponse]
    total: int
    
