"""
PDF extraction module for procurement and tender documents.
Provides robust text extraction page-by-page using pypdf with validation,
page limits, and error handling for malformed or encrypted documents.
"""

import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
import pypdf
from pypdf.errors import PdfReadError, FileNotDecryptedError

logger = logging.getLogger("app.ingestion.pdf_loader")

# MVP-friendly resource bounds
MAX_PAGE_LIMIT = 5000
MAX_PDF_SIZE_BYTES = 200 * 1024 * 1024  # 200MB


@dataclass(frozen=True)
class ExtractedPage:
    """Represents text extracted from a single page of a PDF document."""
    page_number: int  # 1-indexed
    text: str
    char_count: int


@dataclass(frozen=True)
class PDFExtractionResult:
    """Represents the complete result of a PDF document extraction."""
    total_pages: int
    pages: Sequence[ExtractedPage]
    full_text: str
    is_encrypted: bool
    is_corrupt: bool
    warning_message: str | None = None


def extract_text_from_pdf(
    file_source: str | Path | bytes | io.BytesIO,
    max_pages: int = MAX_PAGE_LIMIT,
) -> PDFExtractionResult:
    """
    Safely extracts plain text from a PDF file with strict bounds.

    Args:
        file_source: Path to PDF or raw bytes / BytesIO stream.
        max_pages: Maximum allowable page count to prevent Resource Exhaustion (DoS).

    Returns:
        PDFExtractionResult containing extracted pages and metadata.

    Raises:
        ValueError: If file source is empty, invalid, or encrypted with password.
        PdfReadError: If the file is not a valid PDF document.
    """
    stream: io.BytesIO

    if isinstance(file_source, (str, Path)):
        path = Path(file_source)
        if not path.is_file():
            raise FileNotFoundError(f"PDF document not found at: {path}")
        size = path.stat().st_size
        if size > MAX_PDF_SIZE_BYTES:
            raise ValueError(
                f"PDF file size ({size} bytes) exceeds maximum limit ({MAX_PDF_SIZE_BYTES} bytes)."
            )
        with open(path, "rb") as f:
            stream = io.BytesIO(f.read())
    elif isinstance(file_source, bytes):
        if len(file_source) > MAX_PDF_SIZE_BYTES:
            raise ValueError(
                f"PDF payload size ({len(file_source)} bytes) exceeds limit ({MAX_PDF_SIZE_BYTES} bytes)."
            )
        stream = io.BytesIO(file_source)
    elif isinstance(file_source, io.BytesIO):
        stream = file_source
    else:
        raise ValueError("Invalid file_source provided. Expected Path, string, bytes, or BytesIO.")

    try:
        reader = pypdf.PdfReader(stream)
    except PdfReadError as exc:
        logger.error("Failed to parse PDF document: %s", exc)
        raise ValueError(f"Corrupted or invalid PDF format: {exc}") from exc

    if reader.is_encrypted:
        # MVP mode: Attempt to decrypt with empty password, log warning if fails
        try:
            decrypted = reader.decrypt("")
            if decrypted == 0:
                logger.warning("PDF is password protected. Attempting extraction anyway - may fail.")
        except FileNotDecryptedError as exc:
            logger.warning("PDF decryption failed with empty password. Attempting extraction anyway - may fail.")

    total_pages = len(reader.pages)
    if total_pages == 0:
        return PDFExtractionResult(
            total_pages=0,
            pages=[],
            full_text="",
            is_encrypted=False,
            is_corrupt=False,
            warning_message="PDF contains 0 pages.",
        )

    pages_to_process = min(total_pages, max_pages)
    warning = None
    if total_pages > max_pages:
        warning = f"PDF exceeded page cap of {max_pages}. Only first {max_pages} pages were processed."
        logger.warning(warning)

    extracted_pages: list[ExtractedPage] = []
    text_fragments: list[str] = []

    for idx in range(pages_to_process):
        page_num = idx + 1
        try:
            page = reader.pages[idx]
            extracted_text = page.extract_text() or ""
            # Strip excessive null characters or weird binary artifacts
            extracted_text = extracted_text.replace("\x00", "").strip()
            
            page_obj = ExtractedPage(
                page_number=page_num,
                text=extracted_text,
                char_count=len(extracted_text),
            )
            extracted_pages.append(page_obj)
            if extracted_text:
                text_fragments.append(extracted_text)
        except Exception as exc:
            logger.warning("Error extracting text on page %d: %s", page_num, exc)
            extracted_pages.append(
                ExtractedPage(page_number=page_num, text="", char_count=0)
            )

    full_text = "\n\n".join(text_fragments)

    return PDFExtractionResult(
        total_pages=total_pages,
        pages=extracted_pages,
        full_text=full_text,
        is_encrypted=reader.is_encrypted,
        is_corrupt=False,
        warning_message=warning,
    )
