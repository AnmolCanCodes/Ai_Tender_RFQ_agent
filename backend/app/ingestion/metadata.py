"""
Procurement document metadata extraction module.
Computes document statistics and applies deterministic regex heuristics
to discover tender reference numbers, submission deadlines, estimated values, and EMD.
"""

import re
from dataclasses import dataclass
from typing import Sequence
from app.ingestion.pdf_loader import ExtractedPage

# Heuristic patterns for rapid pre-LLM detection
REF_NO_REGEX = re.compile(
    r"(?:NIT\s*(?:No\.?|Number)|Tender\s*(?:Ref(?:erence)?\.?|Notice|No\.?)|RFP\s*No\.?|Bid\s*Ref\.?)\s*[:\-]?\s*([A-Za-z0-9/\-_]{4,50})",
    re.IGNORECASE,
)
EMD_REGEX = re.compile(
    r"(?:EMD|Earnest\s*Money\s*Deposit|Bid\s*Security)\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
    re.IGNORECASE,
)
DEADLINE_REGEX = re.compile(
    r"(?:Last\s*Date\s*(?:of|for)?\s*Submission|Submission\s*Deadline|Bid\s*Due\s*Date|Closing\s*Date)\s*[:\-]?\s*([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4}(?:\s+[0-9]{1,2}:[0-9]{2}(?:\s*[AaPp][Mm])?)?)",
    re.IGNORECASE,
)
ESTIMATED_VALUE_REGEX = re.compile(
    r"(?:Estimated\s*(?:Cost|Value|Tender\s*Value)|Approx(?:imate)?\s*Value)\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.[0-9]{1,2})?(?:\s*(?:Crore|Lakh|Cr|L))?)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DocumentStats:
    """Statistical summary of document content."""
    total_pages: int
    total_characters: int
    total_words: int
    average_words_per_page: float


@dataclass(frozen=True)
class HeuristicTenderInfo:
    """Heuristically extracted fields found directly in text patterns."""
    detected_reference_number: str | None
    detected_emd_raw: str | None
    detected_deadline_raw: str | None
    detected_estimated_value_raw: str | None


def compute_document_stats(pages: Sequence[ExtractedPage]) -> DocumentStats:
    """Computes basic text statistics across extracted pages."""
    total_pages = len(pages)
    if total_pages == 0:
        return DocumentStats(total_pages=0, total_characters=0, total_words=0, average_words_per_page=0.0)

    total_chars = sum(p.char_count for p in pages)
    total_words = sum(len(p.text.split()) for p in pages)
    avg_words = total_words / total_pages if total_pages > 0 else 0.0

    return DocumentStats(
        total_pages=total_pages,
        total_characters=total_chars,
        total_words=total_words,
        average_words_per_page=round(avg_words, 2),
    )


def extract_heuristic_tender_info(pages: Sequence[ExtractedPage]) -> HeuristicTenderInfo:
    """
    Scans the initial pages (first 5 pages where tender summaries typically reside)
    for prominent identifiers, deadlines, and monetary figures.
    """
    # Look at first 5 pages or all if fewer
    sample_text = "\n".join(p.text for p in pages[:5])

    ref_match = REF_NO_REGEX.search(sample_text)
    emd_match = EMD_REGEX.search(sample_text)
    deadline_match = DEADLINE_REGEX.search(sample_text)
    val_match = ESTIMATED_VALUE_REGEX.search(sample_text)

    return HeuristicTenderInfo(
        detected_reference_number=ref_match.group(1).strip() if ref_match else None,
        detected_emd_raw=emd_match.group(1).strip() if emd_match else None,
        detected_deadline_raw=deadline_match.group(1).strip() if deadline_match else None,
        detected_estimated_value_raw=val_match.group(1).strip() if val_match else None,
    )
