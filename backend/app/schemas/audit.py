from datetime import datetime

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: int
    organization_id: int
    user_id: int | None
    tender_id: int | None
    action: str
    entity_type: str
    entity_id: int | None
    metadata_json: str | None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
