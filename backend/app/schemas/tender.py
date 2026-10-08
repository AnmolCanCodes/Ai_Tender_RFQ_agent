from datetime import datetime

from pydantic import BaseModel


class TenderCreate(BaseModel):
    title: str
    reference_number: str | None = None
    issuing_organization: str | None = None
    description: str | None = None
    estimated_value: float | None = None
    submission_deadline: datetime | None = None


class TenderUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    submission_deadline: datetime | None = None


class TenderResponse(BaseModel):
    id: int
    title: str
    reference_number: str | None
    issuing_organization: str | None
    description: str | None
    estimated_value: float | None
    submission_deadline: datetime | None
    status: str

    model_config = {
        "from_attributes": True
    }