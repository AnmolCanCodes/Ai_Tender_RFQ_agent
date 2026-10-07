"""
Document service managing procurement file uploads, storage, and lifecycle.
Enforces file format validations, directory traversal protections,
SHA-256 integrity checks, and tenant-scoped storage hierarchies.
"""

from datetime import datetime
import logging
import os
from pathlib import Path
from typing import BinaryIO, Sequence
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.tender import Tender
from app.utils.helper import compute_file_sha256, record_audit_log, sanitize_filename

logger = logging.getLogger("app.services.document_service")

# Base directory for storing uploaded procurement documents
UPLOAD_BASE_DIR = Path("uploads")
MAX_FILE_SIZE_BYTES = 200 * 1024 * 1024  # 200 MB (MVP-friendly)
ALLOWED_MIME_TYPES = {"application/pdf"}
ALLOWED_EXTENSIONS = {".pdf"}


def _ensure_storage_dir(organization_id: int, tender_id: int) -> Path:
    """Creates isolated folder structure per tenant organization and tender."""
    target_dir = UPLOAD_BASE_DIR / f"org_{organization_id}" / f"tender_{tender_id}"
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def upload_document(
    db: Session,
    organization_id: int,
    user_id: int,
    tender_id: int,
    file: UploadFile,
) -> Document:
    """
    Validates, saves, and registers a tender document.

    Args:
        db: Active database session.
        organization_id: Tenant organization ID.
        user_id: Uploading user ID.
        tender_id: Target tender ID.
        file: Uploaded file stream from FastAPI.

    Returns:
        Persisted Document model instance.
    """
    # 1. Verify tender exists (MVP mode: relaxed org boundary check)
    tender = db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tender not found.",
        )

    # 2. Validate filename and extension
    original_filename = file.filename or "document.pdf"
    safe_name = sanitize_filename(original_filename)
    ext = os.path.splitext(safe_name)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Only PDF documents are accepted.",
        )

    # 3. Stream file to disk and check file size
    storage_dir = _ensure_storage_dir(organization_id, tender_id)
    # Prefix timestamp to guarantee unique disk paths
    timestamp_prefix = int(datetime.utcnow().timestamp())
    dest_path = storage_dir / f"{timestamp_prefix}_{safe_name}"

    total_bytes = 0
    try:
        with open(dest_path, "wb") as out_f:
            while chunk := file.file.read(65536):
                total_bytes += len(chunk)
                if total_bytes > MAX_FILE_SIZE_BYTES:
                    # Clean up partial file on size violation
                    out_f.close()
                    dest_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum size limit of {MAX_FILE_SIZE_BYTES // (1024*1024)} MB.",
                    )
                out_f.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        dest_path.unlink(missing_ok=True)
        logger.error("Failed to write uploaded file to disk: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while saving the file.",
        ) from exc

    # 4. Compute SHA-256 for integrity and deduplication
    file_sha256 = compute_file_sha256(dest_path)

    # 5. Persist Document record
    document = Document(
        tender_id=tender.id,
        filename=safe_name,
        storage_path=str(dest_path.resolve()),
        file_size=total_bytes,
        mime_type=file.content_type or "application/pdf",
        page_count=None,
        file_hash=file_sha256,
        processing_status="UPLOADED",
    )

    db.add(document)
    db.flush()

    record_audit_log(
        db=db,
        organization_id=organization_id,
        user_id=user_id,
        tender_id=tender.id,
        action="UPLOAD_DOCUMENT",
        entity_type="Document",
        entity_id=document.id,
        metadata={"filename": safe_name, "file_size": total_bytes, "sha256": file_sha256},
    )

    db.commit()
    db.refresh(document)
    return document


def get_document_by_id(
    db: Session,
    organization_id: int,
    document_id: int,
) -> Document:
    """Retrieves document by primary key ID (MVP mode: relaxed org boundary check)."""
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    return doc


def list_documents_for_tender(
    db: Session,
    organization_id: int,
    tender_id: int,
) -> Sequence[Document]:
    """Lists all documents registered under a specific tender (MVP mode: relaxed org check)."""
    # Verify tender exists
    tender = db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tender not found.",
        )

    return (
        db.query(Document)
        .filter(Document.tender_id == tender_id)
        .order_by(Document.created_at.desc())
        .all()
    )


def delete_document(
    db: Session,
    organization_id: int,
    user_id: int,
    document_id: int,
) -> bool:
    """Deletes document record and associated physical file on disk."""
    doc = get_document_by_id(db, organization_id, document_id)
    tender_id = doc.tender_id

    # Remove file on disk if exists
    try:
        path = Path(doc.storage_path)
        if path.is_file():
            path.unlink(missing_ok=True)
    except Exception as exc:
        logger.warning("Failed to delete physical file %s: %s", doc.storage_path, exc)

    record_audit_log(
        db=db,
        organization_id=organization_id,
        user_id=user_id,
        tender_id=tender_id,
        action="DELETE_DOCUMENT",
        entity_type="Document",
        entity_id=doc.id,
        metadata={"filename": doc.filename},
    )

    db.delete(doc)
    db.commit()
    return True
