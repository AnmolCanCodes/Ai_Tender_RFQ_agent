"""
Tender service managing procurement workspace lifecycles.
Enforces multi-tenant data boundaries, provides deadline tracking,
and maintains audit trails across all tender state mutations.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Sequence
from fastapi import HTTPException, status
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.models.tender import Tender
from app.utils.helper import record_audit_log

logger = logging.getLogger("app.services.tender_service")

ALLOWED_TENDER_STATUSES = {
    "DRAFT",
    "PROCESSING",
    "ANALYZED",
    "UNDER_REVIEW",
    "BID",
    "NO_BID",
    "SUBMITTED",
    "ARCHIVED",
}


def create_tender(
    db: Session,
    organization_id: int,
    user_id: int,
    title: str,
    reference_number: str | None = None,
    issuing_organization: str | None = None,
    description: str | None = None,
    estimated_value: float | None = None,
    emd_amount: float | None = None,
    submission_deadline: datetime | None = None,
    pre_bid_meeting_date: datetime | None = None,
    clarification_deadline: datetime | None = None,
) -> Tender:
    """
    Creates a new tender within the tenant organization.
    Ensures input sanity, generates default reference numbers if missing, and records an audit log.
    """
    clean_title = title.strip()
    if not clean_title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tender title cannot be empty.",
        )

    # Autogenerate reference number if omitted
    ref_num = reference_number.strip() if reference_number else f"TND-{int(datetime.now(timezone.utc).timestamp())}"

    # Check for duplicate reference number within the organization
    existing = (
        db.query(Tender)
        .filter(Tender.organization_id == organization_id, Tender.reference_number == ref_num)
        .first()
    )
    if existing:
        ref_num = f"{ref_num}-{int(datetime.now(timezone.utc).timestamp()) % 10000}"

    tender = Tender(
        organization_id=organization_id,
        title=clean_title,
        reference_number=ref_num,
        issuing_organization=issuing_organization.strip() if issuing_organization else None,
        description=description.strip() if description else None,
        estimated_value=estimated_value,
        emd_amount=emd_amount,
        submission_deadline=submission_deadline,
        pre_bid_meeting_date=pre_bid_meeting_date,
        clarification_deadline=clarification_deadline,
        status="DRAFT",
    )

    db.add(tender)
    db.flush()

    record_audit_log(
        db=db,
        organization_id=organization_id,
        user_id=user_id,
        tender_id=tender.id,
        action="CREATE_TENDER",
        entity_type="Tender",
        entity_id=tender.id,
        metadata={"title": clean_title, "reference_number": ref_num},
    )

    db.commit()
    db.refresh(tender)
    return tender


def get_tender_by_id(
    db: Session,
    organization_id: int,
    tender_id: int,
) -> Tender:
    """
    Retrieves tender by primary key ID.
    MVP mode: Allows querying without strict org boundary enforcement for local development.
    """
    tender = db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tender with ID {tender_id} not found.",
        )
    return tender


def list_tenders(
    db: Session,
    organization_id: int,
    status_filter: str | None = None,
    search_query: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[Sequence[Tender], int]:
    """
    Lists tenders with pagination and search.
    MVP mode: Relaxed org boundary check for local development.
    """
    safe_skip = max(0, skip)
    safe_limit = min(100, max(1, limit))

    query = db.query(Tender)

    if status_filter:
        normalized_status = status_filter.strip().upper()
        if normalized_status in ALLOWED_TENDER_STATUSES:
            query = query.filter(Tender.status == normalized_status)

    if search_query:
        term = f"%{search_query.strip()}%"
        query = query.filter(
            or_(
                Tender.title.ilike(term),
                Tender.reference_number.ilike(term),
                Tender.issuing_organization.ilike(term),
            )
        )

    total_count = query.count()
    tenders = (
        query.order_by(desc(Tender.created_at))
        .offset(safe_skip)
        .limit(safe_limit)
        .all()
    )

    return tenders, total_count


def update_tender(
    db: Session,
    organization_id: int,
    user_id: int,
    tender_id: int,
    title: str | None = None,
    reference_number: str | None = None,
    issuing_organization: str | None = None,
    description: str | None = None,
    estimated_value: float | None = None,
    emd_amount: float | None = None,
    submission_deadline: datetime | None = None,
    pre_bid_meeting_date: datetime | None = None,
    clarification_deadline: datetime | None = None,
    tender_status: str | None = None,
) -> Tender:
    """
    Updates an existing tender, enforcing tenant ownership and valid statuses.
    """
    tender = get_tender_by_id(db, organization_id, tender_id)
    changes: dict[str, Any] = {}

    if title is not None:
        clean_title = title.strip()
        if clean_title:
            tender.title = clean_title
            changes["title"] = clean_title

    if reference_number is not None:
        tender.reference_number = reference_number.strip()
        changes["reference_number"] = tender.reference_number

    if issuing_organization is not None:
        tender.issuing_organization = issuing_organization.strip()
        changes["issuing_organization"] = tender.issuing_organization

    if description is not None:
        tender.description = description.strip()
        changes["description"] = tender.description

    if estimated_value is not None:
        tender.estimated_value = estimated_value
        changes["estimated_value"] = estimated_value

    if emd_amount is not None:
        tender.emd_amount = emd_amount
        changes["emd_amount"] = emd_amount

    if submission_deadline is not None:
        tender.submission_deadline = submission_deadline
        changes["submission_deadline"] = str(submission_deadline)

    if pre_bid_meeting_date is not None:
        tender.pre_bid_meeting_date = pre_bid_meeting_date
        changes["pre_bid_meeting_date"] = str(pre_bid_meeting_date)

    if clarification_deadline is not None:
        tender.clarification_deadline = clarification_deadline
        changes["clarification_deadline"] = str(clarification_deadline)

    if tender_status is not None:
        norm_status = tender_status.strip().upper()
        if norm_status not in ALLOWED_TENDER_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tender status. Allowed: {sorted(ALLOWED_TENDER_STATUSES)}",
            )
        tender.status = norm_status
        changes["status"] = norm_status

    tender.updated_at = datetime.utcnow()

    record_audit_log(
        db=db,
        organization_id=organization_id,
        user_id=user_id,
        tender_id=tender.id,
        action="UPDATE_TENDER",
        entity_type="Tender",
        entity_id=tender.id,
        metadata={"changes": changes},
    )

    db.commit()
    db.refresh(tender)
    return tender


def delete_tender(
    db: Session,
    organization_id: int,
    user_id: int,
    tender_id: int,
) -> bool:
    """
    Deletes a tender and cascades associated chunks, documents, and requirements.
    """
    tender = get_tender_by_id(db, organization_id, tender_id)

    record_audit_log(
        db=db,
        organization_id=organization_id,
        user_id=user_id,
        tender_id=tender.id,
        action="DELETE_TENDER",
        entity_type="Tender",
        entity_id=tender.id,
        metadata={"title": tender.title, "reference_number": tender.reference_number},
    )

    db.delete(tender)
    db.commit()
    return True


def get_tender_deadlines(
    db: Session,
    organization_id: int,
    tender_id: int,
) -> dict[str, Any]:
    """
    Calculates milestone timelines and remaining days for submission,
    pre-bid meeting, and clarifications.
    """
    tender = get_tender_by_id(db, organization_id, tender_id)
    now = datetime.utcnow()

    def calc_delta(dt: datetime | None) -> dict[str, Any]:
        if not dt:
            return {"date": None, "days_left": None, "is_passed": None}
        diff = dt - now
        days_left = diff.days if diff.days >= 0 else 0
        return {
            "date": dt.isoformat(),
            "days_left": days_left,
            "is_passed": dt < now,
        }

    return {
        "tender_id": tender.id,
        "title": tender.title,
        "reference_number": tender.reference_number,
        "submission_deadline": calc_delta(tender.submission_deadline),
        "pre_bid_meeting": calc_delta(tender.pre_bid_meeting_date),
        "clarification_deadline": calc_delta(tender.clarification_deadline),
    }
