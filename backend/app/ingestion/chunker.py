from dataclasses import dataclass
from typing import Sequence
from app.ingestion.pdf_loader import ExtractedPage


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata."""
    content: str
    page_number: int
    section: str | None
    chunk_index: int


def chunk_text(
    text: str,
    chunk_size: int = 1500,
    overlap: int = 200
):
    """Legacy function for backward compatibility."""
    chunks = []

    start = 0

    while start < len(text):
        end = start + chunk_size

        chunks.append(
            text[start:end]
        )

        start += chunk_size - overlap

    return chunks


def chunk_extracted_pages(
    pages: Sequence[ExtractedPage],
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[TextChunk]:
    """
    Chunks extracted PDF pages into smaller segments with overlap.
    Preserves page number and attempts to detect section headers.
    """
    chunks: list[TextChunk] = []
    chunk_index = 0

    for page in pages:
        text = page.text
        if not text or len(text.strip()) < 10:
            continue

        start = 0
        while start < len(text):
            end = start + chunk_size

            chunk_content = text[start:end]

            section = None
            if start == 0:
                first_line = chunk_content.split("\n")[0].strip()
                if len(first_line) < 100 and first_line:
                    section = first_line

            chunks.append(
                TextChunk(
                    content=chunk_content,
                    page_number=page.page_number,
                    section=section,
                    chunk_index=chunk_index
                )
            )

            chunk_index += 1
            start += chunk_size - chunk_overlap

    return chunks


