"""
Document upload, inspection, and background processing endpoints.
"""

from typing import Sequence
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.document import DocumentResponse
from app.services.document_service import (
    delete_document,
    get_document_by_id,
    list_documents_for_tender,
    upload_document,
)
from app.utils.dependencies import get_current_user
from app.workers.document_worker import process_tender_document

router = APIRouter(tags=["Documents"])


@router.post(
    "/tenders/{tender_id}/documents/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_tender_file(
    tender_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    auto_process: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Uploads a procurement PDF document for a tender and automatically initiates
    background ingestion, chunking, and AI requirement extraction.
    """
    doc = upload_document(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        tender_id=tender_id,
        file=file,
    )

    if auto_process:
        background_tasks.add_task(
            process_tender_document,
            document_id=doc.id,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
        )

    return doc


@router.get(
    "/tenders/{tender_id}/documents/",
    response_model=list[DocumentResponse],
)
def get_documents_list(
    tender_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists all uploaded documents under the specified tender."""
    docs = list_documents_for_tender(db, current_user.organization_id, tender_id)
    return docs


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
)
def get_single_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves document metadata and current processing status."""
    return get_document_by_id(db, current_user.organization_id, document_id)


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes document record and associated disk storage."""
    delete_document(db, current_user.organization_id, current_user.id, document_id)
    return None


@router.post("/documents/{document_id}/process")
def trigger_processing(
    document_id: int,
    background_tasks: BackgroundTasks,
    sync: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Triggers or restarts document text extraction, chunking, and requirement analysis."""
    # Verify existence & ownership
    doc = get_document_by_id(db, current_user.organization_id, document_id)

    if sync:
        result = process_tender_document(
            document_id=doc.id,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
        )
        return result

    background_tasks.add_task(
        process_tender_document,
        document_id=doc.id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return {"message": "Document processing task scheduled in background.", "document_id": doc.id}
