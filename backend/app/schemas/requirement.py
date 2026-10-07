from datetime import datetime
from pydantic import BaseModel


class RequirementResponse(BaseModel):
    id: int
    category: str
    title: str
    description: str
    source_page: int | None = None
    source_section: str | None = None
    mandatory: bool
    status: str
    match_status: str
    matched_evidence: str | None = None
    verification_notes: str | None = None
    is_checklist_item: bool
    checklist_completed: bool
    checklist_notes: str | None = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class RequirementVerificationRequest(BaseModel):
    status: str  # VERIFIED or REJECTED
    notes: str | None = None


class ChecklistUpdateRequest(BaseModel):
    completed: bool
    notes: str | None = None