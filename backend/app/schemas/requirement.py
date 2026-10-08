from pydantic import BaseModel


class RequirementResponse(BaseModel):
    id: int
    category: str
    title: str
    description: str
    source_page: int | None
    mandatory: bool
    status: str

    model_config = {
        "from_attributes": True
    }


class RequirementUpdate(BaseModel):
    status: str | None = None
    mandatory: bool | None = None