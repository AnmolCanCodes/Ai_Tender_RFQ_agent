from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.company import CompanyProfileCreate, CompanyProfileResponse
from app.services.matching_service import (
    get_company_profile,
    upsert_company_profile,
)
from app.utils.dependencies import get_current_user

router = APIRouter(
    prefix="/company-profile",
    tags=["Company Profile"]
)


class CompanyProfileUpdate(BaseModel):
    legal_name: str | None = None
    annual_turnover: float | None = None
    years_experience: int | None = None
    gst_number: str | None = None
    website: str | None = None
    certifications: str | None = None
    technical_capabilities: str | None = None
    past_contracts_count: int | None = None
    past_experience_summary: str | None = None
    description: str | None = None


@router.post(
    "",
    response_model=CompanyProfileResponse
)
def create(
    data: CompanyProfileCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return upsert_company_profile(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        legal_name=data.legal_name,
        annual_turnover=data.annual_turnover,
        years_experience=data.years_experience,
        gst_number=data.gst_number,
        website=data.website,
        description=data.description
    )


@router.get(
    "",
    response_model=CompanyProfileResponse
)
def get(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_company_profile(
        db=db,
        organization_id=current_user.organization_id
    )


@router.put(
    "",
    response_model=CompanyProfileResponse
)
def update(
    data: CompanyProfileUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return upsert_company_profile(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        legal_name=data.legal_name or "",
        annual_turnover=data.annual_turnover,
        years_experience=data.years_experience,
        gst_number=data.gst_number,
        website=data.website,
        certifications=data.certifications,
        technical_capabilities=data.technical_capabilities,
        past_contracts_count=data.past_contracts_count,
        past_experience_summary=data.past_experience_summary,
        description=data.description
    )
