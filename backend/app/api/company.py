"""
Company profile endpoints for managing corporate capabilities, turnover, and certifications.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.company import CompanyProfileCreate, CompanyProfileResponse
from app.services.matching_service import get_company_profile, upsert_company_profile
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/company", tags=["Company Profile"])


@router.get("/profile", response_model=CompanyProfileResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves authenticated organization's company profile."""
    return get_company_profile(db, current_user.organization_id)


@router.put("/profile", response_model=CompanyProfileResponse)
def save_profile(
    payload: CompanyProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Creates or updates company credentials for automated capability matching."""
    return upsert_company_profile(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        legal_name=payload.legal_name,
        annual_turnover=payload.annual_turnover,
        years_experience=payload.years_experience,
        gst_number=payload.gst_number,
        website=payload.website,
        certifications=payload.certifications,
        technical_capabilities=payload.technical_capabilities,
        past_contracts_count=payload.past_contracts_count,
        past_experience_summary=payload.past_experience_summary,
        description=payload.description,
    )
