"""
Structured extraction module for procurement documents.
Converts unstructured tender text into strongly-typed domain structures
for tender overviews and categorised legal/technical requirements.
"""

import json
import logging
import re
from typing import Any, Sequence

from app.ai.llm import HuggingFaceLLMClient, get_llm_client
from app.ai.prompts import (
    REQUIREMENTS_EXTRACTION_SYSTEM,
    REQUIREMENTS_EXTRACTION_USER_PROMPT,
    TENDER_OVERVIEW_EXTRACTION_SYSTEM,
    TENDER_OVERVIEW_USER_PROMPT,
)
from app.ingestion.chunker import ProcessedChunk
from app.utils.helper import sanitize_prompt_input

logger = logging.getLogger("app.ai.extraction")

VALID_CATEGORIES = {
    "ELIGIBILITY",
    "FINANCIAL",
    "TECHNICAL",
    "DOCUMENTATION",
    "COMPLIANCE",
    "COMMERCIAL",
    "DELIVERY",
}


def _extract_json_block(text: str) -> str:
    """
    Strips markdown code fences and isolates valid JSON payload.
    """
    trimmed = text.strip()
    # Strip markdown fence if present
    if trimmed.startswith("```"):
        lines = trimmed.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        trimmed = "\n".join(lines).strip()

    # Search for json object or array boundaries if text has preamble
    if not (trimmed.startswith("{") or trimmed.startswith("[")):
        obj_match = re.search(r"(\[.*\]|\{.*\})", trimmed, re.DOTALL)
        if obj_match:
            trimmed = obj_match.group(1).strip()

    return trimmed


def _heuristic_requirement_fallback(text: str) -> list[dict[str, Any]]:
    """
    Deterministic rule-based extraction fallback when LLM is unavailable.
    Identifies common procurement clauses from standard text patterns.
    """
    fallback_requirements: list[dict[str, Any]] = []
    lines = text.splitlines()

    for line in lines:
        l_lower = line.lower()
        if "gst" in l_lower and ("registration" in l_lower or "certificate" in l_lower or "valid" in l_lower):
            fallback_requirements.append({
                "category": "ELIGIBILITY",
                "title": "GST Registration",
                "description": line.strip(),
                "source_page": 1,
                "source_section": "Eligibility Criteria",
                "mandatory": True,
                "is_checklist_item": True,
            })
        elif "turnover" in l_lower:
            fallback_requirements.append({
                "category": "FINANCIAL",
                "title": "Annual Turnover Requirement",
                "description": line.strip(),
                "source_page": 1,
                "source_section": "Financial Criteria",
                "mandatory": True,
                "is_checklist_item": True,
            })
        elif "experience" in l_lower and ("year" in l_lower or "contract" in l_lower):
            fallback_requirements.append({
                "category": "ELIGIBILITY",
                "title": "Relevant Work Experience",
                "description": line.strip(),
                "source_page": 1,
                "source_section": "Eligibility Criteria",
                "mandatory": True,
                "is_checklist_item": True,
            })
        elif "iso" in l_lower and ("9001" in l_lower or "27001" in l_lower or "14001" in l_lower or "certificate" in l_lower):
            fallback_requirements.append({
                "category": "TECHNICAL",
                "title": "Quality Certification (ISO)",
                "description": line.strip(),
                "source_page": 1,
                "source_section": "Technical Specifications",
                "mandatory": False,
                "is_checklist_item": True,
            })
        elif "emd" in l_lower or "earnest money" in l_lower:
            fallback_requirements.append({
                "category": "DOCUMENTATION",
                "title": "Earnest Money Deposit (EMD)",
                "description": line.strip(),
                "source_page": 1,
                "source_section": "Submission Instructions",
                "mandatory": True,
                "is_checklist_item": True,
            })
        elif "penalty" in l_lower or "liquidated damages" in l_lower:
            fallback_requirements.append({
                "category": "DELIVERY",
                "title": "Liquidated Damages / Delay Penalty",
                "description": line.strip(),
                "source_page": 1,
                "source_section": "Delivery Terms",
                "mandatory": True,
                "is_checklist_item": False,
            })

    # Return deduplicated by title
    seen = set()
    deduped = []
    for r in fallback_requirements:
        if r["title"] not in seen:
            seen.add(r["title"])
            deduped.append(r)

    return deduped


def extract_tender_overview(
    document_text: str,
    client: HuggingFaceLLMClient | None = None,
) -> dict[str, Any]:
    """
    Extracts high-level tender overview fields using LLM inference with graceful recovery.
    """
    active_client = client or get_llm_client()
    sample_text = sanitize_prompt_input(document_text, max_chars=12000)

    prompt = TENDER_OVERVIEW_USER_PROMPT.format(document_text=sample_text)

    try:
        raw_output = active_client.generate(
            prompt=prompt,
            system_prompt=TENDER_OVERVIEW_EXTRACTION_SYSTEM,
            temperature=0.1,
            max_tokens=1000,
        )
        json_str = _extract_json_block(raw_output)
        data = json.loads(json_str)

        if isinstance(data, dict):
            # Normalize numeric fields
            est_val = data.get("estimated_value")
            if est_val is not None:
                try:
                    data["estimated_value"] = float(str(est_val).replace(",", "").strip())
                except (ValueError, TypeError):
                    data["estimated_value"] = None

            emd = data.get("emd_amount")
            if emd is not None:
                try:
                    data["emd_amount"] = float(str(emd).replace(",", "").strip())
                except (ValueError, TypeError):
                    data["emd_amount"] = None

            return data

    except Exception as exc:
        logger.warning("LLM tender overview extraction failed: %s. Using default structure.", exc)

    # Fallback default dictionary
    return {
        "title": "Tender Document",
        "reference_number": "TENDER-UNSPECIFIED",
        "issuing_organization": None,
        "description": None,
        "estimated_value": None,
        "emd_amount": None,
        "submission_deadline": None,
        "pre_bid_meeting_date": None,
        "clarification_deadline": None,
    }


def extract_requirements_from_chunks(
    chunks: Sequence[ProcessedChunk],
    client: HuggingFaceLLMClient | None = None,
) -> list[dict[str, Any]]:
    """
    Extracts structured requirements from document chunks with provenance (page and section).
    """
    active_client = client or get_llm_client()
    
    # Collate chunks with page tags
    content_lines: list[str] = []
    for c in chunks:
        sec_tag = f" Section: {c.section}" if c.section else ""
        content_lines.append(f"[Page {c.page_number}{sec_tag}]\n{c.content}")

    combined_text = "\n\n---\n\n".join(content_lines)
    sanitized_text = sanitize_prompt_input(combined_text, max_chars=20000)

    prompt = REQUIREMENTS_EXTRACTION_USER_PROMPT.format(content=sanitized_text)

    try:
        raw_output = active_client.generate(
            prompt=prompt,
            system_prompt=REQUIREMENTS_EXTRACTION_SYSTEM,
            temperature=0.1,
            max_tokens=3000,
        )
        json_str = _extract_json_block(raw_output)
        data = json.loads(json_str)

        if isinstance(data, list):
            valid_items: list[dict[str, Any]] = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                cat = str(item.get("category", "")).upper()
                if cat not in VALID_CATEGORIES:
                    cat = "TECHNICAL"
                
                valid_items.append({
                    "category": cat,
                    "title": str(item.get("title", "Requirement"))[:300],
                    "description": str(item.get("description", "")),
                    "source_page": int(item["source_page"]) if item.get("source_page") is not None else None,
                    "source_section": str(item.get("source_section", ""))[:255] if item.get("source_section") else None,
                    "mandatory": bool(item.get("mandatory", False)),
                    "is_checklist_item": bool(item.get("is_checklist_item", False)),
                })

            if valid_items:
                return valid_items

    except Exception as exc:
        logger.warning("LLM requirement extraction failed: %s. Using deterministic fallback.", exc)

    # Deterministic fallback
    return _heuristic_requirement_fallback(sanitized_text)
