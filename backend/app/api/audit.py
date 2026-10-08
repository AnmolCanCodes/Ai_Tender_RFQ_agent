from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.utils.dependencies import get_current_user

router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"]
)


@router.get(
    "",
    response_model=list[AuditLog]
)
def list_logs(
    tender_id: int | None = None,
    entity_type: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    query = db.query(AuditLog).filter(
        AuditLog.organization_id == current_user.organization_id
    )

    if tender_id:
        query = query.filter(AuditLog.tender_id == tender_id)

    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type.upper())

    return query.order_by(AuditLog.created_at.desc()).limit(100).all()
