from dataclasses import dataclass
from pypdf import PdfReader


@dataclass
class ExtractedPage:
    """Represents a single page extracted from a PDF document."""
    page_number: int
    text: str
    char_count: int


@dataclass
class PDFExtractionResult:
    """Result of PDF text extraction operation."""
    total_pages: int
    pages: list[ExtractedPage]


def extract_text_from_pdf(path: str) -> PDFExtractionResult:
    """Extracts text from all pages of a PDF file."""
    reader = PdfReader(path)

    pages = []

    for page_number, page in enumerate(
        reader.pages,
        start=1
    ):
        text = page.extract_text() or ""
        pages.append(
            ExtractedPage(
                page_number=page_number,
                text=text,
                char_count=len(text)
            )
        )

    return PDFExtractionResult(
        total_pages=len(pages),
        pages=pages
    )


def load_pdf(path: str):
    """Legacy function for backward compatibility."""
    result = extract_text_from_pdf(path)
    return [
        {
            "page_number": page.page_number,
            "text": page.text
        }
        for page in result.pages
    ]
