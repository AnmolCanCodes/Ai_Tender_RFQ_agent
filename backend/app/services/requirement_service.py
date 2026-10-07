"""
Requirement management service for procurement tenders.
Supports category querying, human verification workflows,
audit trails, and interactive submission checklist completion tracking.
"""

from datetime import datetime
import logging
from typing import Any, Sequence
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.requirement import Requirement
from app.models.tender import Tender
from app.utils.helper import record_audit_log

logger = logging.getLogger("app.services.requirement_service")

ALLOWED_VERIFICATION_STATUSES = {"PENDING", "VERIFIED", "REJECTED"}
ALLOWED_MATCH_STATUSES = {"PENDING", "MATCHED", "PARTIAL", "MISSING", "REQUIRES_VERIFICATION"}


def get_requirement_by_id(
    db: Session,
    organization_id: int,
    requirement_id: int,
) -> Requirement:
    """Retrieves requirement by primary key ID (MVP mode: relaxed org boundary check)."""
    req = db.get(Requirement, requirement_id)
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requirement not found.",
        )
    return req


def list_requirements_for_tender(
    db: Session,
    organization_id: int,
    tender_id: int,
    category: str | None = None,
    verification_status: str | None = None,
    match_status: str | None = None,
    mandatory_only: bool | None = None,
    checklist_only: bool | None = None,
) -> Sequence[Requirement]:
    """
    Lists requirements with optional category, status, and checklist filters.
    MVP mode: Relaxed org boundary check for local development.
    """
    # Verify tender exists
    tender = db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tender not found.",
        )

    query = db.query(Requirement).filter(Requirement.tender_id == tender_id)

    if category:
        query = query.filter(Requirement.category == category.strip().upper())
    if verification_status:
        query = query.filter(Requirement.status == verification_status.strip().upper())
    if match_status:
        query = query.filter(Requirement.match_status == match_status.strip().upper())
    if mandatory_only is not None:
        query = query.filter(Requirement.mandatory == mandatory_only)
    if checklist_only is not None:
        query = query.filter(Requirement.is_checklist_item == checklist_only)

    return query.order_by(Requirement.id.asc()).all()


def update_requirement_verification(
    db: Session,
    organization_id: int,
    user_id: int,
    requirement_id: int,
    verification_status: str,
    notes: str | None = None,
) -> Requirement:
    """
    Executes human verification action on an extracted requirement.
    Fulfills human-in-the-loop requirement auditing.
    """
    req = get_requirement_by_id(db, organization_id, requirement_id)
    norm_status = verification_status.strip().upper()

    if norm_status not in ALLOWED_VERIFICATION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification status. Allowed: {sorted(ALLOWED_VERIFICATION_STATUSES)}",
        )

    req.status = norm_status
    if notes is not None:
        req.verification_notes = notes.strip()

    record_audit_log(
        db=db,
        organization_id=organization_id,
        user_id=user_id,
        tender_id=req.tender_id,
        action="VERIFY_REQUIREMENT",
        entity_type="Requirement",
        entity_id=req.id,
        metadata={"status": norm_status, "notes": notes},
    )

    db.commit()
    db.refresh(req)
    return req


def update_checklist_item(
    db: Session,
    organization_id: int,
    user_id: int,
    requirement_id: int,
    completed: bool,
    notes: str | None = None,
) -> Requirement:
    """
    Updates completion status and notes for a submission checklist requirement item.
    """
    req = get_requirement_by_id(db, organization_id, requirement_id)

    req.is_checklist_item = True
    req.checklist_completed = completed
    if notes is not None:
        req.checklist_notes = notes.strip()

    record_audit_log(
        db=db,
        organization_id=organization_id,
        user_id=user_id,
        tender_id=req.tender_id,
        action="UPDATE_CHECKLIST_ITEM",
        entity_type="Requirement",
        entity_id=req.id,
        metadata={"completed": completed, "notes": notes},
    )

    db.commit()
    db.refresh(req)
    return req


def get_tender_checklist_summary(
    db: Session,
    organization_id: int,
    tender_id: int,
) -> dict[str, Any]:
    """
    Calculates progress metrics for the tender submission checklist.
    MVP mode: Relaxed org boundary check for local development.
    """
    # Verify tender exists
    tender = db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tender not found.",
        )

    checklist_items = (
        db.query(Requirement)
        .filter(
            Requirement.tender_id == tender_id,
            (Requirement.is_checklist_item == True) | (Requirement.category == "DOCUMENTATION"),
        )
        .all()
    )

    total_items = len(checklist_items)
    completed_items = sum(1 for item in checklist_items if item.checklist_completed)
    pending_items = total_items - completed_items
    completion_percentage = round((completed_items / total_items) * 100, 1) if total_items > 0 else 100.0

    return {
        "tender_id": tender_id,
        "total_items": total_items,
        "completed_items": completed_items,
        "pending_items": pending_items,
        "completion_percentage": completion_percentage,
        "items": [
            {
                "id": it.id,
                "title": it.title,
                "category": it.category,
                "mandatory": it.mandatory,
                "completed": it.checklist_completed,
                "notes": it.checklist_notes,
                "source_page": it.source_page,
            }
            for it in checklist_items
        ],
    }
