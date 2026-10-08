from fastapi import APIRouter, Depends, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.document import DocumentResponse
from app.services.document_service import (
    delete_document,
    get_document_by_id,
    list_documents_for_tender,
    upload_document,
)
from app.utils.dependencies import get_current_user

router = APIRouter(
    prefix="/tenders/{tender_id}/documents",
    tags=["Documents"]
)


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED
)
def upload(
    tender_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return upload_document(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        tender_id=tender_id,
        file=file
    )


@router.get(
    "",
    response_model=list[DocumentResponse]
)
def list_docs(
    tender_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return list_documents_for_tender(
        db=db,
        organization_id=current_user.organization_id,
        tender_id=tender_id
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse
)
def get_one(
    tender_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_document_by_id(
        db=db,
        organization_id=current_user.organization_id,
        document_id=document_id
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete(
    tender_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    delete_document(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        document_id=document_id
    )
    return None
