"""
LLM-based structured extraction module for tender documents.
Extracts tender overview metadata and categorized requirements from document chunks.
"""

import json
import logging
from typing import Any
from app.ai.llm import get_llm_client
from app.ai.prompts import TENDER_OVERVIEW_SYSTEM, TENDER_OVERVIEW_USER_PROMPT, REQUIREMENT_EXTRACTION_SYSTEM, REQUIREMENT_EXTRACTION_USER_PROMPT
from app.utils.helper import sanitize_prompt_input

logger = logging.getLogger("app.ai.extraction")


def extract_tender_overview(sample_text: str) -> dict[str, Any]:
    """
    Extracts structured tender overview metadata from sample document text.
    Uses LLM to identify title, reference number, issuing organization, EMD, deadline, and value.
    """
    if not sample_text or len(sample_text.strip()) < 100:
        return {}

    try:
        client = get_llm_client()
        clean_sample = sanitize_prompt_input(sample_text, max_chars=8000)

        prompt = TENDER_OVERVIEW_USER_PROMPT.format(text=clean_sample)

        response = client.generate(
            prompt=prompt,
            system_prompt=TENDER_OVERVIEW_SYSTEM,
            temperature=0.1,
            max_tokens=1000,
        )

        if response:
            try:
                overview = json.loads(response)
                return overview
            except json.JSONDecodeError:
                logger.warning("Failed to parse tender overview JSON from LLM response")
                return {}

    except Exception as exc:
        logger.error("Tender overview extraction failed: %s", exc)

    return {}


def extract_requirements_from_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Extracts categorized requirements from document chunks using LLM.
    Returns list of requirement dictionaries with category, title, description, mandatory flag, and source.
    """
    if not chunks:
        return []

    requirements: list[dict[str, Any]] = []

    try:
        client = get_llm_client()

        for chunk in chunks:
            content = chunk.get("content", "")
            if not content or len(content.strip()) < 50:
                continue

            clean_content = sanitize_prompt_input(content, max_chars=4000)

            prompt = REQUIREMENT_EXTRACTION_USER_PROMPT.format(text=clean_content)

            try:
                response = client.generate(
                    prompt=prompt,
                    system_prompt=REQUIREMENT_EXTRACTION_SYSTEM,
                    temperature=0.1,
                    max_tokens=1500,
                )

                if response:
                    try:
                        extracted = json.loads(response)
                        reqs = extracted.get("requirements", [])

                        for req in reqs:
                            req_obj = {
                                "category": req.get("category", "GENERAL").upper(),
                                "title": req.get("title", "Untitled Requirement")[:300],
                                "description": req.get("description", "")[:2000],
                                "mandatory": req.get("mandatory", False),
                                "is_checklist_item": req.get("category", "").upper() in ["DOCUMENTATION", "COMPLIANCE"],
                                "source_page": chunk.get("page_number"),
                                "source_section": chunk.get("section"),
                            }
                            requirements.append(req_obj)

                    except json.JSONDecodeError:
                        logger.warning("Failed to parse requirement extraction JSON")
                        continue

            except Exception as exc:
                logger.warning("Requirement extraction failed for chunk: %s", exc)
                continue

    except Exception as exc:
        logger.error("Batch requirement extraction failed: %s", exc)

    return requirements
