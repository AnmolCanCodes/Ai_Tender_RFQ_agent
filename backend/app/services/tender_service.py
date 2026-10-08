from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.tender import Tender
from app.models.user import User
from app.schemas.tender import TenderCreate


def create_tender(db:Session, user:User, data:TenderCreate):
    tender = Tender(
        organization_id = user.organization_id,
        title = data.title,
        reference_number = data.reference_number,
        issuing_organization = data.issuing_organization,
        description = data.description,
        estimated_value = data.estimated_value,
        submission_deadline = data.submission_deadline,
        status = "DRAFT"
    )

    db.add(tender)
    db.commit()
    db.refresh(tender)

    return tender


def get_tender(db:Session,user:User,tender_id: int):
    tender = (
        db.query(Tender).filter(Tender.id == tender_id, Tender.organization_id == user.organization_id).first()
    )

    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    return tender