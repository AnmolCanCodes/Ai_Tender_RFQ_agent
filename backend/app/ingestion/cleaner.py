"""
Text cleaning and normalization pipeline for tender and RFQ documents.
Cleans raw OCR/PDF text, strips recurring headers/footers, normalizes currency
symbols, and ensures consistent structure for downstream chunking and LLM analysis.
"""

import re
from typing import Sequence

# Common header/footer patterns: "Page X of Y", "Tender Ref: ...", standalone page numbers
PAGE_NUM_PATTERN = re.compile(r"^\s*(page\s+\d+(\s+of\s+\d+)?|\d+)\s*$", re.IGNORECASE)
MULTIPLE_NEWLINES_PATTERN = re.compile(r"\n{3,}")
MULTIPLE_SPACES_PATTERN = re.compile(r"[ \t]{2,}")
CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_page_text(raw_text: str) -> str:
    """
    Cleans a single page of extracted text.
    Removes control characters, normalizes line breaks, and trims unnecessary whitespace.
    """
    if not raw_text or not isinstance(raw_text, str):
        return ""

    # Strip null bytes and non-printable control characters
    text = CONTROL_CHARS_PATTERN.sub("", raw_text)

    # Normalize unicode spaces and dashes
    text = text.replace("\u00a0", " ")  # Non-breaking space
    text = text.replace("\u2013", "-").replace("\u2014", "-")  # En/em dash
    text = text.replace("\u2018", "'").replace("\u2019", "'")  # Smart quotes
    text = text.replace("\u201c", '"').replace("\u201d", '"')

    # Normalize standard bullets
    text = re.sub(r"[\u2022\u2023\u25e6\u2043\u2219]", "\n- ", text)

    lines = text.splitlines()
    cleaned_lines: list[str] = []

    for line in lines:
        stripped_line = MULTIPLE_SPACES_PATTERN.sub(" ", line).strip()
        # Filter out standalone page numbering lines
        if PAGE_NUM_PATTERN.match(stripped_line):
            continue
        cleaned_lines.append(stripped_line)

    result = "\n".join(cleaned_lines)
    # Collapse 3+ newlines into 2 (preserving paragraph breaks)
    result = MULTIPLE_NEWLINES_PATTERN.sub("\n\n", result)
    return result.strip()


def remove_repetitive_headers_and_footers(pages_text: Sequence[str]) -> list[str]:
    """
    Detects lines that repeat across more than 50% of the pages (likely headers/footers)
    and removes them to avoid polluting chunk embeddings.
    """
    if len(pages_text) < 4:
        return [clean_page_text(p) for p in pages_text]

    first_lines: dict[str, int] = {}
    last_lines: dict[str, int] = {}
    cleaned_pages = [clean_page_text(p) for p in pages_text]

    for page in cleaned_pages:
        lines = [ln.strip() for ln in page.splitlines() if ln.strip()]
        if lines:
            first = lines[0]
            last = lines[-1]
            first_lines[first] = first_lines.get(first, 0) + 1
            last_lines[last] = last_lines.get(last, 0) + 1

    threshold = len(pages_text) * 0.5
    frequent_first = {line for line, cnt in first_lines.items() if cnt >= threshold and len(line) > 3}
    frequent_last = {line for line, cnt in last_lines.items() if cnt >= threshold and len(line) > 3}

    sanitized_pages: list[str] = []
    for page in cleaned_pages:
        lines = [ln.strip() for ln in page.splitlines() if ln.strip()]
        if not lines:
            sanitized_pages.append("")
            continue

        if lines and lines[0] in frequent_first:
            lines = lines[1:]
        if lines and lines[-1] in frequent_last:
            lines = lines[:-1]

        sanitized_pages.append("\n".join(lines))

    return sanitized_pages
