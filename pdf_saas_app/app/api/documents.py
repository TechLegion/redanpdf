import os
import shutil
import tempfile
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import uuid
from datetime import datetime
from PIL import Image
from sqlalchemy import func

from app.db.session import get_db
from app.db.models import User, Document
from app.services.auth_services import get_current_active_user
from app.services.storage_service import StorageService
from app.core.pdf_operations import PDFProcessor

router = APIRouter()
storage_service = StorageService()
pdf_processor = PDFProcessor()

class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_size: int
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload a PDF document
    """
    # Validate file is a PDF
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF"
        )
    
    # Create temp file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    try:
        # Save uploaded file to temp location
        with temp_file as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Get file size
        file_size = os.path.getsize(temp_file.name)
        
        # Extract text content for later use with AI
        text_content = pdf_processor.extract_text(temp_file.name)
        
        # Upload to storage
        file_path = storage_service.upload_file(temp_file.name, file.filename)
        
        # Save document in database
        db_document = Document(
            filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            mime_type="application/pdf",
            owner_id=current_user.id,
            text_content=text_content
        )
        
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        
        return db_document
    
    finally:
        # Clean up temp file
        if os.path.exists(temp_file.name):
            os.remove(temp_file.name)

@router.get("/list", response_model=List[DocumentResponse])
async def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all documents owned by the current user
    """
    documents = db.query(Document).filter(Document.owner_id == current_user.id).all()
    return documents

@router.get("/{document_id}")
async def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a document by ID
    """
    document = db.query(Document).filter(Document.id == document_id, Document.owner_id == current_user.id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Update last accessed timestamp
    document.last_accessed = func.now()
    db.commit()
    
    # Get the file from storage and return it
    local_file_path = storage_service.get_file(document.file_path)
    return FileResponse(
        local_file_path,
        media_type="application/pdf",
        filename=document.filename
    )

@router.post("/merge")
async def merge_documents(
    document_ids: List[str] = Form(...),
    output_filename: str = Form("merged.pdf"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Merge multiple documents into a single PDF
    """
    # Check that all documents exist and are owned by the user
    pdf_paths = []
    for doc_id in document_ids:
        document = db.query(Document).filter(Document.id == doc_id, Document.owner_id == current_user.id).first()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {doc_id} not found or not owned by user"
            )
        
        # Get file from storage
        local_file_path = storage_service.get_file(document.file_path)
        pdf_paths.append(local_file_path)
    
    # Create temp output file
    output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf').name
    
    try:
        # Merge PDFs
        pdf_processor.merge_pdfs(pdf_paths, output_path)
        
        # Get merged file size
        file_size = os.path.getsize(output_path)
        
        # Extract text content
        text_content = pdf_processor.extract_text(output_path)
        
        # Upload merged file to storage
        file_path = storage_service.upload_file(output_path, output_filename)
        
        # Save document in database
        db_document = Document(
            filename=output_filename,
            file_path=file_path,
            file_size=file_size,
            mime_type="application/pdf",
            owner_id=current_user.id,
            text_content=text_content
        )
        
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        
        return {
            "id": db_document.id,
            "filename": db_document.filename,
            "message": "Documents merged successfully"
        }
    
    finally:
        # Clean up temp files
        if os.path.exists(output_path):
            os.remove(output_path)

@router.post("/{document_id}/watermark", response_model=DocumentResponse)
async def add_watermark(
    document_id: str,
    watermark_text: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Add a watermark to a PDF document
    """
    # Get document
    document = db.query(Document).filter(Document.id == document_id, Document.owner_id == current_user.id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Get file from storage
    local_file_path = storage_service.get_file(document.file_path)
    
    # Create temp output file
    output_filename = f"watermarked_{document.filename}"
    output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf').name
    
    try:
        # Add watermark
        pdf_processor.add_watermark(local_file_path, watermark_text, output_path)
        
        # Get file size
        file_size = os.path.getsize(output_path)
        
        # Extract text content
        text_content = pdf_processor.extract_text(output_path)
        
        # Upload to storage
        file_path = storage_service.upload_file(output_path, output_filename)
        
        # Save document in database
        db_document = Document(
            filename=output_filename,
            file_path=file_path,
            file_size=file_size,
            mime_type="application/pdf",
            owner_id=current_user.id,
            text_content=text_content
        )
        
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        
        return db_document
    
    finally:
        # Clean up temp files
        if os.path.exists(output_path):
            os.remove(output_path)

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a document
    """
    document = db.query(Document).filter(Document.id == document_id, Document.owner_id == current_user.id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Delete from storage
    storage_service.delete_file(document.file_path)
    
    # Delete from database
    db.delete(document)
    db.commit()
    
    return {"message": "Document deleted successfully"}

@router.get("/{document_id}/extract-text")
async def extract_text_from_pdf(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    document = db.query(Document).filter(Document.id == document_id, Document.owner_id == current_user.id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    text = pdf_processor.extract_text(document.file_path)
    return {"text": text}

@router.post("/{document_id}/compress", response_model=DocumentResponse)
async def compress_pdf(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    document = db.query(Document).filter(Document.id == document_id, Document.owner_id == current_user.id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    output_filename = f"compressed_{document.filename}"
    output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf').name
    pdf_processor.compress_pdf(document.file_path, output_path)
    file_size = os.path.getsize(output_path)
    text_content = pdf_processor.extract_text(output_path)
    file_path = storage_service.upload_file(output_path, output_filename)
    db_document = Document(
        filename=output_filename,
        file_path=file_path,
        file_size=file_size,
        mime_type="application/pdf",
        owner_id=current_user.id,
        text_content=text_content
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    if os.path.exists(output_path):
        os.remove(output_path)
    return db_document

@router.post("/image-to-pdf", response_model=DocumentResponse)
async def image_to_pdf(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    images = []
    for file in files:
        img = Image.open(file.file).convert("RGB")
        images.append(img)
    output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf').name
    images[0].save(output_path, save_all=True, append_images=images[1:])
    output_filename = "images_to_pdf.pdf"
    file_size = os.path.getsize(output_path)
    text_content = pdf_processor.extract_text(output_path)
    file_path = storage_service.upload_file(output_path, output_filename)
    db_document = Document(
        filename=output_filename,
        file_path=file_path,
        file_size=file_size,
        mime_type="application/pdf",
        owner_id=current_user.id,
        text_content=text_content
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    if os.path.exists(output_path):
        os.remove(output_path)
    return db_document