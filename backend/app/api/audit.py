"""
Audit trail inspection endpoints for procurement governance.
"""

from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.tender import Tender
from app.models.user import User
from app.utils.dependencies import get_current_user

router = APIRouter(tags=["Audit Logs"])


@router.get("/tenders/{tender_id}/audit-logs")
def get_tender_audit_logs(
    tender_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves immutable audit trail entries recorded for a specific tender."""
    # Enforce tenant ownership of tender
    tender = (
        db.query(Tender)
        .filter(Tender.id == tender_id, Tender.organization_id == current_user.organization_id)
        .first()
    )
    if not tender:
        return []

    logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.organization_id == current_user.organization_id,
            AuditLog.tender_id == tender_id,
        )
        .order_by(desc(AuditLog.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": l.id,
            "action": l.action,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "user_id": l.user_id,
            "metadata": l.metadata_json,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]


@router.get("/audit-logs")
def get_organization_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves organizational governance logs across all tenders and actions."""
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.organization_id == current_user.organization_id)
        .order_by(desc(AuditLog.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": l.id,
            "action": l.action,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "tender_id": l.tender_id,
            "user_id": l.user_id,
            "metadata": l.metadata_json,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]
