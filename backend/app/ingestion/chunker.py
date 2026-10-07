"""
Procurement-aware document chunker.
Splits cleaned text into contextual chunks while maintaining page numbers,
clause / section headers, and chunk sequences for vector indexing and precise citations.
"""

import re
from dataclasses import dataclass
from typing import Sequence
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ingestion.pdf_loader import ExtractedPage

# Regex to detect legal / procurement section headers
# Examples: "Section 3.1", "Clause 4", "PART A - ELIGIBILITY", "5. TECHNICAL SPECIFICATIONS"
SECTION_HEADER_PATTERN = re.compile(
    r"^(?:(?:section|clause|chapter|part|item|annexure|schedule|appendix)\s+[\w\.\-]+(?:\s*[:-]\s*.*)?|"
    r"(?:\d+\.(?:\d+\.?)?)\s+[A-Z][A-Za-z0-9\s,-]+|"
    r"[A-Z\s]{4,}(?:REQUIREMENTS|ELIGIBILITY|CRITERIA|SPECIFICATIONS|SCOPE OF WORK|TERMS AND CONDITIONS))",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True)
class ProcessedChunk:
    """Represents a text chunk ready for vector embedding and database insertion."""
    page_number: int
    section: str | None
    chunk_index: int
    content: str
    char_count: int


def detect_section_header(text: str, fallback_section: str | None = None) -> str | None:
    """
    Scans text chunk for a clause, section, or chapter title.
    Returns the first matched header or the provided fallback.
    """
    match = SECTION_HEADER_PATTERN.search(text)
    if match:
        matched_str = match.group(0).strip()
        # Cap section string length
        return matched_str[:200]
    return fallback_section


def chunk_extracted_pages(
    pages: Sequence[ExtractedPage],
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[ProcessedChunk]:
    """
    Splits a sequence of extracted document pages into structured chunks.
    Ensures that each chunk preserves its originating page number and detected section.

    Args:
        pages: Sequence of ExtractedPage instances.
        chunk_size: Target character size per chunk.
        chunk_overlap: Overlap characters to maintain context across chunk boundaries.

    Returns:
        List of ProcessedChunk objects ready for vector storage.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", "; ", " ", ""],
        length_function=len,
    )

    processed_chunks: list[ProcessedChunk] = []
    global_chunk_index = 0
    current_detected_section: str | None = None

    for page in pages:
        if not page.text.strip():
            continue

        raw_chunks = splitter.split_text(page.text)
        for chunk_text in raw_chunks:
            cleaned_chunk = chunk_text.strip()
            if not cleaned_chunk:
                continue

            # Update current section if page/chunk introduced a new section header
            detected_sec = detect_section_header(cleaned_chunk, current_detected_section)
            if detected_sec:
                current_detected_section = detected_sec

            chunk_obj = ProcessedChunk(
                page_number=page.page_number,
                section=current_detected_section,
                chunk_index=global_chunk_index,
                content=cleaned_chunk,
                char_count=len(cleaned_chunk),
            )
            processed_chunks.append(chunk_obj)
            global_chunk_index += 1

    return processed_chunks
