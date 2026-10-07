"""
Tender workspace management endpoints.
"""

from typing import Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.tender import TenderCreate, TenderListResponse, TenderResponse, TenderUpdate
from app.services.tender_service import (
    create_tender,
    delete_tender,
    get_tender_by_id,
    get_tender_deadlines,
    list_tenders,
    update_tender,
)
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/tenders", tags=["Tenders"])


@router.post("/", response_model=TenderResponse, status_code=status.HTTP_201_CREATED)
def create_new_tender(
    payload: TenderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Creates a new tender in the current user's organization."""
    tender = create_tender(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        title=payload.title,
        reference_number=payload.reference_number,
        issuing_organization=payload.issuing_organization,
        description=payload.description,
        estimated_value=payload.estimated_value,
        emd_amount=payload.emd_amount,
        submission_deadline=payload.submission_deadline,
        pre_bid_meeting_date=payload.pre_bid_meeting_date,
        clarification_deadline=payload.clarification_deadline,
    )
    return tender


@router.get("/", response_model=TenderListResponse)
def get_all_tenders(
    status: str | None = None,
    search: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists organization tenders with filtering and pagination."""
    items, total = list_tenders(
        db=db,
        organization_id=current_user.organization_id,
        status_filter=status,
        search_query=search,
        skip=skip,
        limit=limit,
    )
    return TenderListResponse(
        items=[TenderResponse.model_validate(it) for it in items],
        total=total,
    )


@router.get("/{tender_id}", response_model=TenderResponse)
def get_single_tender(
    tender_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves full details for a single tender."""
    return get_tender_by_id(db, current_user.organization_id, tender_id)


@router.put("/{tender_id}", response_model=TenderResponse)
def update_single_tender(
    tender_id: int,
    payload: TenderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates fields or status for an existing tender."""
    tender = update_tender(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        tender_id=tender_id,
        title=payload.title,
        reference_number=payload.reference_number,
        issuing_organization=payload.issuing_organization,
        description=payload.description,
        estimated_value=payload.estimated_value,
        emd_amount=payload.emd_amount,
        submission_deadline=payload.submission_deadline,
        pre_bid_meeting_date=payload.pre_bid_meeting_date,
        clarification_deadline=payload.clarification_deadline,
        tender_status=payload.status,
    )
    return tender


@router.delete("/{tender_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_tender(
    tender_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes tender and cascades associated documents and requirements."""
    delete_tender(db, current_user.organization_id, current_user.id, tender_id)
    return None


@router.get("/{tender_id}/deadlines")
def get_deadlines(
    tender_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Calculates remaining time for tender submission and clarification deadlines."""
    return get_tender_deadlines(db, current_user.organization_id, tender_id)
