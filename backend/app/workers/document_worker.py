"""
Background document ingestion and intelligence worker.
Executes end-to-end PDF processing, text extraction, semantic chunking,
dense vector embeddings, overview updates, and categorized requirement persistence.
"""

from datetime import datetime
import logging
from typing import Any
from sqlalchemy.orm import Session

from app.ai.embeddings import get_embedding_client
from app.ai.extraction import extract_requirements_from_chunks, extract_tender_overview
from app.core.database import SessionLocal
from app.ingestion.cleaner import clean_page_text, remove_repetitive_headers_and_footers
from app.ingestion.chunker import chunk_extracted_pages
from app.ingestion.pdf_loader import ExtractedPage, extract_text_from_pdf
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.requirement import Requirement
from app.models.tender import Tender
from app.utils.helper import record_audit_log

logger = logging.getLogger("app.workers.document_worker")


def process_tender_document(
    document_id: int,
    organization_id: int,
    user_id: int | None = None,
) -> dict[str, Any]:
    """
    Executes the comprehensive processing pipeline for an uploaded tender document.
    Runs in background worker or task queue with isolated database session and transaction management.

    Steps:
    1. Lock & mark document as PROCESSING.
    2. Extract PDF pages safely.
    3. Clean and sanitize text.
    4. Chunk text with procurement header detection.
    5. Generate dense 384-d vector embeddings.
    6. Persist chunks in database.
    7. Extract and apply tender overview metadata.
    8. Extract categorized requirements and populate database.
    9. Mark document PROCESSED and tender ANALYZED.
    """
    db: Session = SessionLocal()
    try:
        # 1. Fetch document and parent tender
        doc = (
            db.query(Document)
            .join(Tender, Document.tender_id == Tender.id)
            .filter(Document.id == document_id, Tender.organization_id == organization_id)
            .first()
        )
        if not doc:
            logger.error("Worker could not find document %d for org %d", document_id, organization_id)
            return {"status": "error", "message": "Document not found."}

        tender = doc.tender

        # Update processing statuses
        doc.processing_status = "PROCESSING"
        tender.status = "PROCESSING"
        db.commit()

        logger.info("Starting processing for Document %d (Tender %d)", doc.id, tender.id)

        # 2. Extract PDF text
        pdf_res = extract_text_from_pdf(doc.storage_path)
        doc.page_count = pdf_res.total_pages
        raw_texts = [p.text for p in pdf_res.pages]

        # 3. Clean pages
        cleaned_texts = remove_repetitive_headers_and_footers(raw_texts)
        pages_for_chunking = [
            ExtractedPage(page_number=idx, text=txt, char_count=len(txt))
            for idx, txt in enumerate(cleaned_texts, 1)
            if txt.strip()
        ]

        # 4. Chunk pages
        chunks = chunk_extracted_pages(pages_for_chunking, chunk_size=1000, chunk_overlap=150)
        logger.info("Generated %d chunks for Document %d", len(chunks), doc.id)

        # 5. Generate embeddings
        embedder = get_embedding_client()
        chunk_texts = [c.content for c in chunks]
        embeddings = embedder.embed_batch(chunk_texts)

        # 6. Delete old chunks for this document if re-processing (idempotency)
        db.query(Chunk).filter(Chunk.document_id == doc.id).delete()

        # Persist new chunks
        for c, emb in zip(chunks, embeddings):
            chunk_rec = Chunk(
                document_id=doc.id,
                tender_id=tender.id,
                content=c.content,
                page_number=c.page_number,
                section=c.section,
                chunk_index=c.chunk_index,
                embedding=emb,
            )
            db.add(chunk_rec)

        db.flush()

        # 7. Extract tender overview metadata
        full_sample_text = "\n\n".join(cleaned_texts[:8])
        overview = extract_tender_overview(full_sample_text)

        if overview.get("title") and tender.title in ("Tender Document", "Untitled Tender", ""):
            tender.title = str(overview["title"])[:300]

        if overview.get("reference_number") and tender.reference_number.startswith("TND-"):
            tender.reference_number = str(overview["reference_number"])[:100]

        if overview.get("issuing_organization") and not tender.issuing_organization:
            tender.issuing_organization = str(overview["issuing_organization"])[:255]

        if overview.get("description") and not tender.description:
            tender.description = str(overview["description"])

        if overview.get("estimated_value") is not None and tender.estimated_value is None:
            tender.estimated_value = overview["estimated_value"]

        if overview.get("emd_amount") is not None and tender.emd_amount is None:
            tender.emd_amount = overview["emd_amount"]

        # Parse date if string
        if overview.get("submission_deadline") and tender.submission_deadline is None:
            try:
                tender.submission_deadline = datetime.fromisoformat(str(overview["submission_deadline"]))
            except (ValueError, TypeError):
                pass

        # 8. Extract requirements
        extracted_reqs = extract_requirements_from_chunks(chunks)
        logger.info("Extracted %d requirements for Tender %d", len(extracted_reqs), tender.id)

        # Clear existing unverified requirements to prevent duplicates upon re-processing
        db.query(Requirement).filter(
            Requirement.tender_id == tender.id,
            Requirement.source_document_id == doc.id,
            Requirement.status == "PENDING",
        ).delete()

        for req_data in extracted_reqs:
            req_model = Requirement(
                tender_id=tender.id,
                category=req_data["category"],
                title=req_data["title"],
                description=req_data["description"],
                source_document_id=doc.id,
                source_page=req_data.get("source_page"),
                source_section=req_data.get("source_section"),
                mandatory=req_data.get("mandatory", False),
                is_checklist_item=req_data.get("is_checklist_item", False),
                status="PENDING",
                match_status="PENDING",
            )
            db.add(req_model)

        # 9. Mark completion
        doc.processing_status = "PROCESSED"
        doc.error_message = None
        tender.status = "ANALYZED"
        tender.updated_at = datetime.utcnow()

        record_audit_log(
            db=db,
            organization_id=organization_id,
            user_id=user_id,
            tender_id=tender.id,
            action="DOCUMENT_PROCESSED",
            entity_type="Document",
            entity_id=doc.id,
            metadata={
                "chunks_count": len(chunks),
                "requirements_count": len(extracted_reqs),
                "page_count": doc.page_count,
            },
        )

        db.commit()
        logger.info("Successfully finished processing Document %d", doc.id)

        return {
            "status": "success",
            "document_id": doc.id,
            "chunks_count": len(chunks),
            "requirements_count": len(extracted_reqs),
        }

    except Exception as exc:
        db.rollback()
        logger.error("Document processing encountered unhandled error: %s", exc, exc_info=True)
        # Attempt to mark document as FAILED in fresh transaction
        try:
            error_doc = db.get(Document, document_id)
            if error_doc:
                error_doc.processing_status = "FAILED"
                error_doc.error_message = str(exc)[:1000]
                if error_doc.tender:
                    error_doc.tender.status = "FAILED"
                db.commit()
        except Exception:
            pass

        return {"status": "error", "message": str(exc)}

    finally:
        db.close()
