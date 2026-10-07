"""
AI Tender Intelligence endpoints: Evidence-based RAG Q&A and Bid Readiness Analysis.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.rag import AnswerResponse, BidReadinessResponse, QuestionRequest
from app.services.matching_service import answer_tender_question, run_bid_readiness_analysis
from app.utils.dependencies import get_current_user

router = APIRouter(tags=["AI Intelligence"])


@router.post(
    "/tenders/{tender_id}/rag/query",
    response_model=AnswerResponse,
)
def ask_tender_question(
    tender_id: int,
    payload: QuestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Asks natural language question about tender terms and retrieves answers
    backed by exact source citations (page numbers and sections).
    """
    return answer_tender_question(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        tender_id=tender_id,
        question=payload.question,
    )


@router.post(
    "/tenders/{tender_id}/readiness",
    response_model=BidReadinessResponse,
)
def evaluate_bid_readiness(
    tender_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Compares company profile against tender requirements to generate
    an evidence-backed Bid/No-Bid readiness score and identifies critical risk gaps.
    """
    return run_bid_readiness_analysis(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        tender_id=tender_id,
    )
