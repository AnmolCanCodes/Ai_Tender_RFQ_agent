from pydantic import BaseModel, EmailStr, model_validator


class RegisterRequest(BaseModel):
    organization_name: str | None = None
    full_name: str
    email: EmailStr
    password: str

    @model_validator(mode="after")
    def resolve_org_name(self) -> "RegisterRequest":
        name = self.organization_name or self.organsiation_name
        if not name or not name.strip():
            raise ValueError("organization_name must not be empty.")
        self.organization_name = name.strip()
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    organization_id: int
    email: EmailStr
    full_name: str
    role: str

    model_config = {
        "from_attributes": True
    }