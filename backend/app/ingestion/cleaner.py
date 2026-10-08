import re
from typing import Sequence


def clean_text(text: str) -> str:
    """Legacy function for backward compatibility."""
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def clean_page_text(text: str) -> str:
    """
    Cleans extracted PDF page text by removing null bytes,
    excessive whitespace, and non-printable control characters.
    """
    if not text:
        return ""

    cleaned = text.replace("\x00", "")
    cleaned = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned.strip()


def remove_repetitive_headers_and_footers(page_texts: Sequence[str]) -> list[str]:
    """
    Detects and removes repetitive header/footer text across pages.
    Simple heuristic: if a line appears on 50%+ of pages, it's likely a header/footer.
    """
    if not page_texts or len(page_texts) < 2:
        return list(page_texts)

    all_lines = []
    for page_text in page_texts:
        lines = page_text.split("\n")
        all_lines.extend([line.strip() for line in lines if line.strip()])

    line_counts = {}
    for line in all_lines:
        line_counts[line] = line_counts.get(line, 0) + 1

    threshold = len(page_texts) // 2
    repetitive_lines = {line for line, count in line_counts.items() if count >= threshold}

    cleaned_pages = []
    for page_text in page_texts:
        lines = page_text.split("\n")
        filtered_lines = [
            line for line in lines
            if line.strip() not in repetitive_lines or len(line.strip()) > 100
        ]
        cleaned_pages.append("\n".join(filtered_lines))

    return cleaned_pages
