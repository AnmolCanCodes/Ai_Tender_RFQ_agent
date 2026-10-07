"""
Requirement management and submission checklist endpoints.
"""

from typing import Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.requirement import (
    ChecklistUpdateRequest,
    RequirementResponse,
    RequirementVerificationRequest,
)
from app.services.requirement_service import (
    get_tender_checklist_summary,
    list_requirements_for_tender,
    update_checklist_item,
    update_requirement_verification,
)
from app.utils.dependencies import get_current_user

router = APIRouter(tags=["Requirements & Checklist"])


@router.get(
    "/tenders/{tender_id}/requirements/",
    response_model=list[RequirementResponse],
)
def get_requirements(
    tender_id: int,
    category: str | None = None,
    verification_status: str | None = None,
    match_status: str | None = None,
    mandatory_only: bool | None = None,
    checklist_only: bool | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists categorized legal, financial, and technical requirements for a tender."""
    return list_requirements_for_tender(
        db=db,
        organization_id=current_user.organization_id,
        tender_id=tender_id,
        category=category,
        verification_status=verification_status,
        match_status=match_status,
        mandatory_only=mandatory_only,
        checklist_only=checklist_only,
    )


@router.post(
    "/requirements/{requirement_id}/verify",
    response_model=RequirementResponse,
)
def verify_requirement(
    requirement_id: int,
    payload: RequirementVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submits a human verification decision (VERIFIED / REJECTED) with audit notes.
    """
    return update_requirement_verification(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        requirement_id=requirement_id,
        verification_status=payload.status,
        notes=payload.notes,
    )


@router.put(
    "/requirements/{requirement_id}/checklist",
    response_model=RequirementResponse,
)
def update_checklist_status(
    requirement_id: int,
    payload: ChecklistUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Marks a required document as completed or adds notes in the submission checklist."""
    return update_checklist_item(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        requirement_id=requirement_id,
        completed=payload.completed,
        notes=payload.notes,
    )


@router.get(
    "/tenders/{tender_id}/checklist",
)
def get_checklist_progress(
    tender_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Calculates completion percentage and lists all required submission documents."""
    return get_tender_checklist_summary(
        db=db,
        organization_id=current_user.organization_id,
        tender_id=tender_id,
    )
