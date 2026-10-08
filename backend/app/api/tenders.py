from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.tender import (TenderCreate,TenderResponse)
from app.services.tender_service import (create_tender,get_tender)
from app.utils.dependencies import get_current_user

router = APIRouter(prefix= "/tenders", tags=["Tenders"] )

@router.post(
    "",
    response_model=TenderResponse
)
def create(
    data: TenderCreate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    return create_tender(db,user,data)

@router.get(
    "/{tender_id}",
    response_model=TenderResponse
)
def get_one(tender_id:int , db: Session  = Depends(get_db), user = Depends(get_current_user)):
    return get_tender(db,user,tender_id)
