"""
Company capability matching and Bid/No-Bid readiness intelligence service.
Evaluates company credentials (turnover, experience, certifications) against
tender requirements, generates readiness reports, and powers evidence-backed RAG Q&A.
"""

from datetime import datetime
import json
import logging
from typing import Any, Sequence
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.ai.llm import get_llm_client
from app.ai.prompts import BID_READINESS_SYSTEM, BID_READINESS_USER_PROMPT, RAG_QA_SYSTEM, RAG_QA_USER_PROMPT
from app.ai.retrieval import format_retrieval_context, retrieve_relevant_chunks
from app.models.company_profile import CompanyProfile
from app.models.requirement import Requirement
from app.models.tender import Tender
from app.utils.helper import record_audit_log, sanitize_prompt_input

logger = logging.getLogger("app.services.matching_service")


def get_company_profile(
    db: Session,
    organization_id: int,
) -> CompanyProfile:
    """Retrieves tenant company profile or raises 404."""
    profile = (
        db.query(CompanyProfile)
        .filter(CompanyProfile.organization_id == organization_id)
        .first()
    )
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company profile not found for this organization.",
        )
    return profile


def upsert_company_profile(
    db: Session,
    organization_id: int,
    user_id: int,
    legal_name: str,
    annual_turnover: float | None = None,
    years_experience: int | None = None,
    gst_number: str | None = None,
    website: str | None = None,
    certifications: str | None = None,
    technical_capabilities: str | None = None,
    past_contracts_count: int | None = None,
    past_experience_summary: str | None = None,
    description: str | None = None,
) -> CompanyProfile:
    """
    Creates or updates the tenant company profile for automated capability matching.
    """
    profile = (
        db.query(CompanyProfile)
        .filter(CompanyProfile.organization_id == organization_id)
        .first()
    )

    clean_legal_name = legal_name.strip()
    if not clean_legal_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Legal name cannot be empty.",
        )

    if not profile:
        profile = CompanyProfile(
            organization_id=organization_id,
            legal_name=clean_legal_name,
            annual_turnover=annual_turnover,
            years_experience=years_experience,
            gst_number=gst_number.strip() if gst_number else None,
            website=website.strip() if website else None,
            certifications=certifications.strip() if certifications else None,
            technical_capabilities=technical_capabilities.strip() if technical_capabilities else None,
            past_contracts_count=past_contracts_count,
            past_experience_summary=past_experience_summary.strip() if past_experience_summary else None,
            description=description.strip() if description else None,
        )
        db.add(profile)
        action = "CREATE_COMPANY_PROFILE"
    else:
        profile.legal_name = clean_legal_name
        if annual_turnover is not None:
            profile.annual_turnover = annual_turnover
        if years_experience is not None:
            profile.years_experience = years_experience
        if gst_number is not None:
            profile.gst_number = gst_number.strip()
        if website is not None:
            profile.website = website.strip()
        if certifications is not None:
            profile.certifications = certifications.strip()
        if technical_capabilities is not None:
            profile.technical_capabilities = technical_capabilities.strip()
        if past_contracts_count is not None:
            profile.past_contracts_count = past_contracts_count
        if past_experience_summary is not None:
            profile.past_experience_summary = past_experience_summary.strip()
        if description is not None:
            profile.description = description.strip()
        profile.updated_at = datetime.utcnow()
        action = "UPDATE_COMPANY_PROFILE"

    db.flush()

    record_audit_log(
        db=db,
        organization_id=organization_id,
        user_id=user_id,
        action=action,
        entity_type="CompanyProfile",
        entity_id=profile.id,
        metadata={"legal_name": clean_legal_name},
    )

    db.commit()
    db.refresh(profile)
    return profile


def evaluate_requirement_match(
    req: Requirement,
    profile: CompanyProfile,
) -> tuple[str, str]:
    """
    Deterministic rule-based requirement evaluator comparing tender criteria
    to verified company attributes.
    Returns (match_status, evidence_string).
    """
    title_desc = f"{req.title} {req.description}".lower()

    # 1. GST Registration Check
    if "gst" in title_desc:
        if profile.gst_number:
            return ("MATCHED", f"Verified company GSTIN: {profile.gst_number}")
        return ("MISSING", "Tender requires GST registration; company profile lacks GST number.")

    # 2. Minimum Annual Turnover Check
    if "turnover" in title_desc:
        if profile.annual_turnover is not None and profile.annual_turnover > 0:
            return ("MATCHED", f"Company annual turnover is ₹{profile.annual_turnover:,.2f}.")
        return ("MISSING", "Tender requires audited turnover; company profile turnover not set.")

    # 3. Years of Experience Check
    if "experience" in title_desc and ("year" in title_desc or "proven" in title_desc):
        if profile.years_experience is not None and profile.years_experience > 0:
            return ("MATCHED", f"Company has {profile.years_experience} years verified domain experience.")
        return ("MISSING", "Tender specifies prior operating years; company experience missing.")

    # 4. Standard Certifications Check (ISO 9001, 27001, 14001, etc.)
    if "iso" in title_desc or "certification" in title_desc:
        certs = (profile.certifications or "").lower()
        if "iso 9001" in title_desc and "iso 9001" in certs:
            return ("MATCHED", "ISO 9001 certificate present in company profile.")
        if "iso 27001" in title_desc and "iso 27001" in certs:
            return ("MATCHED", "ISO 27001 certificate present in company profile.")
        if profile.certifications:
            return ("PARTIAL", f"Company holds certificates [{profile.certifications}]; verification needed for tender clause.")
        return ("MISSING", "Certification required by tender is not found in company credentials.")

    # 5. Previous Government / Public Sector Contracts Check
    if "government contract" in title_desc or "public sector" in title_desc or "work order" in title_desc:
        if profile.past_contracts_count and profile.past_contracts_count > 0:
            return ("MATCHED", f"Company has completed {profile.past_contracts_count} relevant client contracts.")
        return ("MISSING", "Tender requires past government contracts; none recorded in profile.")

    # Default: Requires human specialist verification
    return ("REQUIRES_VERIFICATION", "Requires manual evaluation against company technical portfolio.")


def run_bid_readiness_analysis(
    db: Session,
    organization_id: int,
    user_id: int,
    tender_id: int,
) -> dict[str, Any]:
    """
    Performs full bid readiness evaluation combining deterministic rule checks
    with categorized requirement matrices.
    """
    # 1. Fetch tender and company profile
    tender = (
        db.query(Tender)
        .filter(Tender.id == tender_id, Tender.organization_id == organization_id)
        .first()
    )
    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tender not found.",
        )

    profile = (
        db.query(CompanyProfile)
        .filter(CompanyProfile.organization_id == organization_id)
        .first()
    )
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please configure your company profile before running bid readiness analysis.",
        )

    # 2. Fetch all requirements for tender
    requirements = (
        db.query(Requirement)
        .filter(Requirement.tender_id == tender_id)
        .all()
    )

    if not requirements:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tender has no extracted requirements yet. Please process the document first.",
        )

    # 3. Match each requirement and update DB state
    matched_count = 0
    partial_count = 0
    missing_count = 0
    verification_count = 0
    critical_gaps: list[str] = []

    category_stats: dict[str, dict[str, int]] = {
        "ELIGIBILITY": {"total": 0, "matched": 0},
        "FINANCIAL": {"total": 0, "matched": 0},
        "TECHNICAL": {"total": 0, "matched": 0},
        "DOCUMENTATION": {"total": 0, "matched": 0},
    }

    evaluations: list[dict[str, Any]] = []

    for req in requirements:
        status_val, evidence = evaluate_requirement_match(req, profile)
        req.match_status = status_val
        req.matched_evidence = evidence

        cat = req.category.upper()
        if cat in category_stats:
            category_stats[cat]["total"] += 1

        if status_val == "MATCHED":
            matched_count += 1
            if cat in category_stats:
                category_stats[cat]["matched"] += 1
        elif status_val == "PARTIAL":
            partial_count += 1
            if cat in category_stats:
                category_stats[cat]["matched"] += 0.5
        elif status_val == "MISSING":
            missing_count += 1
            if req.mandatory:
                critical_gaps.append(f"{req.title}: {req.description[:100]}")
        else:
            verification_count += 1

        evaluations.append({
            "requirement_id": req.id,
            "category": req.category,
            "title": req.title,
            "mandatory": req.mandatory,
            "match_status": status_val,
            "evidence": evidence,
            "source_page": req.source_page,
        })

    def calc_score(cat: str) -> float:
        stats = category_stats.get(cat, {"total": 0, "matched": 0})
        total = stats["total"]
        if total == 0:
            return 100.0
        return round((stats["matched"] / total) * 100, 1)

    eligibility_score = calc_score("ELIGIBILITY")
    technical_score = calc_score("TECHNICAL")
    documentation_score = calc_score("DOCUMENTATION")

    overall_avg = round((eligibility_score + technical_score + documentation_score) / 3, 1)
    if overall_avg >= 80 and not critical_gaps:
        overall_readiness = "HIGH"
    elif overall_avg >= 50 and len(critical_gaps) <= 2:
        overall_readiness = "MEDIUM"
    else:
        overall_readiness = "LOW"

    report = {
        "tender_id": tender.id,
        "tender_title": tender.title,
        "eligibility_score": eligibility_score,
        "technical_fit": technical_score,
        "documentation_readiness": documentation_score,
        "overall_readiness": overall_readiness,
        "critical_gaps": critical_gaps,
        "matched_count": matched_count,
        "partial_count": partial_count,
        "missing_count": missing_count,
        "requires_verification_count": verification_count,
        "recommendation": "Human verification required for critical gaps before submission.",
        "requirements": evaluations,
    }

    record_audit_log(
        db=db,
        organization_id=organization_id,
        user_id=user_id,
        tender_id=tender.id,
        action="RUN_BID_READINESS",
        entity_type="Tender",
        entity_id=tender.id,
        metadata={"overall_readiness": overall_readiness, "gaps_count": len(critical_gaps)},
    )

    db.commit()
    return report


def answer_tender_question(
    db: Session,
    organization_id: int,
    user_id: int,
    tender_id: int,
    question: str,
) -> dict[str, Any]:
    """
    Evidence-grounded RAG Question Answering service.
    Retrieves top citations from chunks, builds context, and invokes LLM.
    """
    clean_question = question.strip()
    if not clean_question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty.",
        )

    # 1. Retrieve top relevant chunks for this tender and tenant
    chunks = retrieve_relevant_chunks(
        db=db,
        tender_id=tender_id,
        organization_id=organization_id,
        query=clean_question,
        top_k=5,
    )

    if not chunks:
        return {
            "question": clean_question,
            "answer": "No relevant sections found in the tender documents for this query.",
            "citations": [],
        }

    context = format_retrieval_context(chunks)
    prompt = RAG_QA_USER_PROMPT.format(context=context, question=clean_question)

    client = get_llm_client()
    try:
        answer_text = client.generate(
            prompt=prompt,
            system_prompt=RAG_QA_SYSTEM,
            temperature=0.1,
            max_tokens=1500,
        )
    except Exception as exc:
        logger.error("RAG answer generation failed: %s", exc)
        answer_text = "Service temporarily unavailable to synthesize an answer. Please review the cited document sections below."

    citations = [
        {
            "chunk_id": c.chunk_id,
            "page_number": c.page_number,
            "section": c.section,
            "excerpt": c.content[:300] + ("..." if len(c.content) > 300 else ""),
            "similarity_score": c.similarity_score,
        }
        for c in chunks
    ]

    record_audit_log(
        db=db,
        organization_id=organization_id,
        user_id=user_id,
        tender_id=tender_id,
        action="RAG_QUERY",
        entity_type="Tender",
        entity_id=tender_id,
        metadata={"question": clean_question[:100], "chunks_retrieved": len(chunks)},
    )
    db.commit()

    return {
        "question": clean_question,
        "answer": answer_text,
        "citations": citations,
    }
