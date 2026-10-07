"""
Pydantic schemas for Evidence-Based RAG and Bid Readiness intelligence endpoints.
"""

from typing import Any
from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    """Incoming user natural language query for tender Q&A."""
    question: str = Field(..., min_length=3, max_length=1000, description="Question text")


class Citation(BaseModel):
    """Source provenance citation extracted from indexed tender chunks."""
    chunk_id: int
    page_number: int | None = None
    section: str | None = None
    excerpt: str
    similarity_score: float


class AnswerResponse(BaseModel):
    """AI answer synthesized from evidence chunks with source citations."""
    question: str
    answer: str
    citations: list[Citation]


class RequirementMatchItem(BaseModel):
    requirement_id: int
    category: str
    title: str
    mandatory: bool
    match_status: str
    evidence: str | None = None
    source_page: int | None = None


class BidReadinessResponse(BaseModel):
    """Comprehensive Bid/No-Bid readiness evaluation report."""
    tender_id: int
    tender_title: str
    eligibility_score: float
    technical_fit: float
    documentation_readiness: float
    overall_readiness: str  # HIGH, MEDIUM, LOW
    critical_gaps: list[str]
    matched_count: int
    partial_count: int
    missing_count: int
    requires_verification_count: int
    recommendation: str
    requirements: list[RequirementMatchItem]
