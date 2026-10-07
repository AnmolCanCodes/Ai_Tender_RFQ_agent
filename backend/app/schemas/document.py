from datetime import datetime
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_size: int | None = None
    mime_type: str | None = None
    page_count: int | None = None
    file_hash: str | None = None
    processing_status: str
    error_message: str | None = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }