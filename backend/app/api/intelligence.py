from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.rag import QuestionRequest, AnswerResponse, BidReadinessResponse
from app.services.matching_service import (
    answer_tender_question,
    run_bid_readiness_analysis,
)
from app.utils.dependencies import get_current_user

router = APIRouter(
    prefix="/tenders/{tender_id}/intelligence",
    tags=["Intelligence"]
)


@router.post(
    "/ask",
    response_model=AnswerResponse
)
def ask_question(
    tender_id: int,
    data: QuestionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return answer_tender_question(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        tender_id=tender_id,
        question=data.question
    )


@router.post(
    "/bid-readiness",
    response_model=BidReadinessResponse
)
def bid_readiness(
    tender_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return run_bid_readiness_analysis(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        tender_id=tender_id
    )
