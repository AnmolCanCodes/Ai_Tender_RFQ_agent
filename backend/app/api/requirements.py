from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.requirement import RequirementResponse, RequirementUpdate
from app.services.requirement_service import (
    get_requirement_by_id,
    list_requirements_for_tender,
    update_checklist_item,
    update_requirement_verification,
    get_tender_checklist_summary,
)
from app.utils.dependencies import get_current_user

router = APIRouter(
    prefix="/tenders/{tender_id}/requirements",
    tags=["Requirements"]
)


class VerificationUpdate(BaseModel):
    status: str
    notes: str | None = None


class ChecklistUpdate(BaseModel):
    completed: bool
    notes: str | None = None


@router.get(
    "",
    response_model=list[RequirementResponse]
)
def list_requirements(
    tender_id: int,
    category: str | None = None,
    verification_status: str | None = None,
    match_status: str | None = None,
    mandatory_only: bool | None = None,
    checklist_only: bool | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return list_requirements_for_tender(
        db=db,
        organization_id=current_user.organization_id,
        tender_id=tender_id,
        category=category,
        verification_status=verification_status,
        match_status=match_status,
        mandatory_only=mandatory_only,
        checklist_only=checklist_only
    )


@router.get(
    "/{requirement_id}",
    response_model=RequirementResponse
)
def get_one(
    tender_id: int,
    requirement_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_requirement_by_id(
        db=db,
        organization_id=current_user.organization_id,
        requirement_id=requirement_id
    )


@router.put(
    "/{requirement_id}/verify",
    response_model=RequirementResponse
)
def verify(
    tender_id: int,
    requirement_id: int,
    data: VerificationUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return update_requirement_verification(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        requirement_id=requirement_id,
        verification_status=data.status,
        notes=data.notes
    )


@router.put(
    "/{requirement_id}/checklist",
    response_model=RequirementResponse
)
def update_checklist(
    tender_id: int,
    requirement_id: int,
    data: ChecklistUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return update_checklist_item(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        requirement_id=requirement_id,
        completed=data.completed,
        notes=data.notes
    )


@router.get(
    "/checklist/summary"
)
def checklist_summary(
    tender_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_tender_checklist_summary(
        db=db,
        organization_id=current_user.organization_id,
        tender_id=tender_id
    )
