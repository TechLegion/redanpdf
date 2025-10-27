import os
import shutil
import tempfile
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import uuid
from datetime import datetime
from PIL import Image
from sqlalchemy import func
import subprocess
import time
import logging
import io
import fitz  # PyMuPDF
import hashlib
import mimetypes

from app.db.session import get_db
from app.db.models import User, Document
from app.services.auth_services import get_current_active_user
from app.services.storage_service import StorageService
from app.core.pdf_operations import PDFProcessor
from app.utils.cache import cache_response, invalidate_cache, CacheManager

def validate_file_type(file: UploadFile, allowed_extensions: List[str], allowed_mime_types: List[str]) -> None:
    """
    Validate that the uploaded file has the correct extension and MIME type.
    
    Args:
        file: The uploaded file
        allowed_extensions: List of allowed file extensions (e.g., ['.docx', '.doc'])
        allowed_mime_types: List of allowed MIME types (e.g., ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'])
    
    Raises:
        HTTPException: If the file type is not allowed
    """
    # Check file extension
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Check MIME type
    if file.content_type not in allowed_mime_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid MIME type. Expected one of: {', '.join(allowed_mime_types)}"
        )

router = APIRouter()
pdf_processor = PDFProcessor()
logger = logging.getLogger(__name__)

class DocumentResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    text_content: Optional[str]
    created_at: datetime
    download_url: str
    
    class Config:
        from_attributes = True

class DocumentOperationResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    created_at: datetime
    download_url: str
    message: str = "Operation completed successfully"

    class Config:
        from_attributes = True

@router.post("/upload", response_model=DocumentResponse)
@invalidate_cache("doc_list:*")  # Invalidate document list cache
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload any document file
    """
    # Get file extension and determine file type
    file_extension = os.path.splitext(file.filename)[1].lower()
    
    # Determine file type based on extension
    file_type_mapping = {
        '.pdf': 'pdf',
        '.doc': 'doc',
        '.docx': 'docx',
        '.xls': 'xls',
        '.xlsx': 'xlsx',
        '.ppt': 'ppt',
        '.pptx': 'pptx',
        '.txt': 'txt',
        '.rtf': 'rtf',
        '.odt': 'odt',
        '.ods': 'ods',
        '.odp': 'odp',
        '.csv': 'csv',
        '.jpg': 'jpg',
        '.jpeg': 'jpg',
        '.png': 'png',
        '.gif': 'gif',
        '.bmp': 'bmp',
        '.tiff': 'tiff',
        '.tif': 'tiff'
    }
    
    file_type = file_type_mapping.get(file_extension, 'unknown')
    
    # Create temp file with appropriate suffix
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
    try:
        # Save uploaded file to temp location
        with temp_file as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Compute file hash for deduplication
        def compute_file_hash(file_path):
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        file_hash = compute_file_hash(temp_file.name)
        
        # Check for duplicate for this user
        existing_doc = db.query(Document).filter_by(file_hash=file_hash, owner_id=current_user.id).first()
        if existing_doc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplicate file. Document already uploaded.",
                headers={"X-Existing-Document-ID": existing_doc.id}
            )
        
        # Get file size
        file_size = os.path.getsize(temp_file.name)
        
        # Upload to storage
        storage_service = StorageService()
        file_path = storage_service.upload_file(temp_file.name, file.filename)
        
        # Determine MIME type
        mime_type = file.content_type if file.content_type else 'application/octet-stream'
        
        # Save document in database
        db_document = Document(
            filename=file.filename,
            original_filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            file_type=file_type,
            owner_id=current_user.id,
            owner_email=current_user.email,  # Store email for resilience
            file_hash=file_hash
        )
        
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        
        # Extract text content only for PDFs
        text_content = None
        if file_type == 'pdf':
            try:
                text_content = pdf_processor.extract_text(temp_file.name)
            except Exception as e:
                logger.warning(f"Could not extract text from PDF: {str(e)}")
        
        return DocumentResponse(
            id=db_document.id,
            filename=db_document.filename,
            content_type=mime_type,
            text_content=text_content,
            created_at=db_document.created_at,
            download_url=f"/documents/{db_document.id}/download"
        )
    
    finally:
        # Clean up temp file
        if os.path.exists(temp_file.name):
            os.remove(temp_file.name)

@router.get("/list", response_model=List[DocumentResponse])
@cache_response(ttl=300, key_prefix="doc_list")  # Cache for 5 minutes
async def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all documents owned by the current user (by email)
    """
    # Use email-based filtering for better resilience
    documents = db.query(Document).filter(Document.owner_email == current_user.email).all()
    
    # Convert Document models to DocumentResponse models
    response_documents = []
    for doc in documents:
        # Get text content only for PDFs
        text_content = None
        if doc.file_type == 'pdf':
            text_content = doc.get_text_content()
        
        response_documents.append(DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            content_type=doc.mime_type or "application/octet-stream",
            text_content=text_content,
            created_at=doc.created_at,
            download_url=f"/documents/{doc.id}/download"
        ))
    
    return response_documents

@router.get("/{document_id}", response_model=DocumentResponse)
@cache_response(ttl=600, key_prefix="doc_detail")  # Cache for 10 minutes
async def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get document details by ID (email-based validation)
    """
    document = db.query(Document).filter(Document.id == document_id, Document.owner_email == current_user.email).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Update last accessed timestamp
    document.last_accessed = func.now()
    db.commit()
    
    # Get text content only for PDFs
    text_content = None
    if document.file_type == 'pdf':
        text_content = document.get_text_content()
    
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        content_type=document.mime_type or "application/octet-stream",
        text_content=text_content,
        created_at=document.created_at,
        download_url=f"/documents/{document.id}/download"
    )

@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Download a document by ID (email-based validation)
    """
    document = db.query(Document).filter(Document.id == document_id, Document.owner_email == current_user.email).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    try:
        # Update last accessed timestamp
        document.last_accessed = func.now()
        db.commit()
        # Get the file from storage and return it
        storage_service = StorageService()
        local_file_path = storage_service.get_file(document.file_path)
        return FileResponse(
            local_file_path,
            media_type=document.mime_type or "application/octet-stream",
            filename=document.filename
        )
    except FileNotFoundError as e:
        logger.error(f"File not found for document {document_id}: {str(e)}")
        # Delete the orphaned database record
        db.delete(document)
        db.commit()
        logger.info(f"Deleted orphaned document record: {document_id}")
        raise HTTPException(
            status_code=404,
            detail="The file is no longer available. The document record has been cleaned up. Please upload the file again."
        )

@router.post("/merge", response_model=DocumentOperationResponse)
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
        
        try:
            # Get file from storage
            storage_service = StorageService()
            local_file_path = storage_service.get_file(document.file_path)
            pdf_paths.append(local_file_path)
        except FileNotFoundError as e:
            logger.error(f"File not found for document {doc_id}: {str(e)}")
            # Delete the orphaned database record
            db.delete(document)
            db.commit()
            logger.info(f"Deleted orphaned document record: {doc_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Document {doc_id} is no longer available. The document record has been cleaned up. Please upload the file again."
            )
    
    # Create temp output file
    output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf').name
    
    try:
        # Merge PDFs
        pdf_processor.merge_pdfs(pdf_paths, output_path)
        
        # Get merged file size
        file_size = os.path.getsize(output_path)
        
        # Upload merged file to storage
        storage_service = StorageService()
        file_path = storage_service.upload_file(output_path, output_filename)
        
        # Save document in database
        db_document = Document(
            filename=output_filename,
            original_filename=output_filename,
            file_path=file_path,
            file_size=file_size,
            mime_type="application/pdf",
            owner_id=current_user.id
        )
        
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        
        return DocumentOperationResponse(
            id=db_document.id,
            filename=db_document.filename,
            content_type="application/pdf",
            created_at=db_document.created_at,
            download_url=f"/documents/{db_document.id}/download",
            message="Documents merged successfully"
        )
    
    finally:
        # Clean up temp files
        if os.path.exists(output_path):
            os.remove(output_path)

@router.post("/{document_id}/watermark", response_model=DocumentOperationResponse)
async def add_watermark(
    document_id: str,
    watermark_text: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Add a watermark to a PDF document
    """
    logger.info(f"Watermark request for document {document_id} by user {current_user.id}")
    
    # Get document
    document = db.query(Document).filter(Document.id == document_id, Document.owner_id == current_user.id).first()
    if not document:
        logger.warning(f"Document {document_id} not found or not owned by user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    try:
        # Get file from storage
        storage_service = StorageService()
        local_file_path = storage_service.get_file(document.file_path)
        logger.info(f"Retrieved local file path: {local_file_path}")
        
        # Create temp output file
        output_filename = f"watermarked_{document.filename}"
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf').name
        
        # Add watermark
        logger.info(f"Starting watermark process for {document.filename}")
        pdf_processor.add_watermark(local_file_path, watermark_text, output_path)
        
        # Get file size
        file_size = os.path.getsize(output_path)
        logger.info(f"Watermarked PDF size: {file_size} bytes")
        
        # Upload to storage
        storage_service = StorageService()
        file_path = storage_service.upload_file(output_path, output_filename)
        logger.info(f"Uploaded watermarked PDF to storage: {file_path}")
        
        # Save document in database
        db_document = Document(
            filename=output_filename,
            original_filename=output_filename,
            file_path=file_path,
            file_size=file_size,
            mime_type="application/pdf",
            owner_id=current_user.id
        )
        
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        
        logger.info(f"Successfully created watermarked document with ID: {db_document.id}")
        
        return DocumentOperationResponse(
            id=db_document.id,
            filename=db_document.filename,
            content_type="application/pdf",
            created_at=db_document.created_at,
            download_url=f"/documents/{db_document.id}/download",
            message="Watermark added successfully"
        )
        
    except FileNotFoundError as e:
        logger.error(f"File not found for document {document_id}: {str(e)}")
        # Delete the orphaned database record
        db.delete(document)
        db.commit()
        logger.info(f"Deleted orphaned document record: {document_id}")
        raise HTTPException(
            status_code=404,
            detail="The original file is no longer available. The document record has been cleaned up. Please upload the file again."
        )
    except Exception as e:
        logger.error(f"Error adding watermark to PDF {document_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add watermark: {str(e)}"
        )
    finally:
        # Clean up temp files
        if 'output_path' in locals() and os.path.exists(output_path):
            os.remove(output_path)
            logger.info(f"Cleaned up temporary file: {output_path}")

@router.delete("/{document_id}")
@invalidate_cache("doc_list:*")  # Invalidate document list cache
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
    storage_service = StorageService()
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
    
    try:
        storage_service = StorageService()
        local_file_path = storage_service.get_file(document.file_path)
        text = pdf_processor.extract_text(local_file_path)
        return {"text": text}
    except FileNotFoundError as e:
        logger.error(f"File not found for document {document_id}: {str(e)}")
        # Delete the orphaned database record
        db.delete(document)
        db.commit()
        logger.info(f"Deleted orphaned document record: {document_id}")
        raise HTTPException(
            status_code=404,
            detail="The file is no longer available. The document record has been cleaned up. Please upload the file again."
        )

@router.post("/{document_id}/compress", response_model=DocumentOperationResponse)
@invalidate_cache("doc_list:*")  # Invalidate document list cache
async def compress_pdf(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Compress a PDF document
    """
    logger.info(f"Compress PDF request for document {document_id} by user {current_user.id}")
    
    document = db.query(Document).filter(Document.id == document_id, Document.owner_id == current_user.id).first()
    if not document:
        logger.warning(f"Document {document_id} not found or not owned by user {current_user.id}")
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # Get the local file path
        storage_service = StorageService()
        local_file_path = storage_service.get_file(document.file_path)
        logger.info(f"Retrieved local file path: {local_file_path}")
        logger.info(f"File path type: {type(local_file_path)}")
        logger.info(f"File exists: {os.path.exists(local_file_path)}")
        logger.info(f"File size: {os.path.getsize(local_file_path) if os.path.exists(local_file_path) else 'N/A'}")
        
        output_filename = f"compressed_{document.filename}"
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf').name
        
        # Compress the PDF
        logger.info(f"Starting PDF compression for {document.filename}")
        logger.info(f"Input file path: {local_file_path}")
        logger.info(f"Output file path: {output_path}")
        pdf_processor.compress_pdf(local_file_path, output_path)
        
        # Get file size
        file_size = os.path.getsize(output_path)
        logger.info(f"Compressed PDF size: {file_size} bytes")
        
        # Upload to storage
        storage_service = StorageService()
        file_path = storage_service.upload_file(output_path, output_filename)
        logger.info(f"Uploaded compressed PDF to storage: {file_path}")
        
        # Create new document record
        db_document = Document(
            filename=output_filename,
            original_filename=output_filename,
            file_path=file_path,
            file_size=file_size,
            mime_type="application/pdf",
            owner_id=current_user.id
        )
        
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        
        logger.info(f"Successfully created compressed document with ID: {db_document.id}")
        
        return DocumentOperationResponse(
            id=db_document.id,
            filename=db_document.filename,
            content_type="application/pdf",
            created_at=db_document.created_at,
            download_url=f"/documents/{db_document.id}/download",
            message="PDF compressed successfully"
        )
        
    except FileNotFoundError as e:
        logger.error(f"File not found for document {document_id}: {str(e)}")
        # Delete the orphaned database record
        db.delete(document)
        db.commit()
        logger.info(f"Deleted orphaned document record: {document_id}")
        raise HTTPException(
            status_code=404,
            detail="The original file is no longer available. The document record has been cleaned up. Please upload the file again."
        )
    except Exception as e:
        logger.error(f"Error compressing PDF {document_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compress PDF: {str(e)}"
        )
    finally:
        # Clean up temp file
        if 'output_path' in locals() and os.path.exists(output_path):
            os.remove(output_path)
            logger.info(f"Cleaned up temporary file: {output_path}")

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
    storage_service = StorageService()
    file_path = storage_service.upload_file(output_path, output_filename)
    db_document = Document(
        filename=output_filename,
        original_filename=output_filename,  # Set to output_filename or a concatenation of image names if desired
        file_path=file_path,
        file_size=file_size,
        mime_type="application/pdf",
        owner_id=current_user.id
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    if os.path.exists(output_path):
        os.remove(output_path)
    
    # Return proper DocumentResponse
    return DocumentResponse(
        id=db_document.id,
        filename=db_document.filename,
        content_type="application/pdf",
        text_content=None,  # No text content for image-to-pdf conversion
        created_at=db_document.created_at,
        download_url=f"/documents/{db_document.id}/download"
    )

@router.post("/{document_id}/to-epub")
async def pdf_to_epub(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Convert a PDF document to EPUB format
    """
    document = db.query(Document).filter(Document.id == document_id, Document.owner_id == current_user.id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        storage_service = StorageService()
        local_file_path = storage_service.get_file(document.file_path)
        output_filename = document.filename.rsplit(".", 1)[0] + ".epub"
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.epub').name
        
        pdf_processor.pdf_to_epub(local_file_path, output_path)
        
        # Create a new document record for the EPUB
        file_path = storage_service.upload_file(output_path, output_filename)
        epub_doc = Document(
            filename=output_filename,
            original_filename=output_filename,
            file_path=file_path,
            file_size=os.path.getsize(output_path),
            mime_type="application/epub+zip",
            file_type="epub",
            owner_id=current_user.id
        )
        
        db.add(epub_doc)
        db.commit()
        db.refresh(epub_doc)
        
        return {
            "document_id": epub_doc.id,
            "download_url": f"/documents/{epub_doc.id}/download",
            "filename": output_filename
        }
    except FileNotFoundError as e:
        logger.error(f"File not found for document {document_id}: {str(e)}")
        # Delete the orphaned database record
        db.delete(document)
        db.commit()
        logger.info(f"Deleted orphaned document record: {document_id}")
        raise HTTPException(
            status_code=404,
            detail="The original file is no longer available. The document record has been cleaned up. Please upload the file again."
        )
    finally:
        if 'output_path' in locals() and os.path.exists(output_path):
            os.remove(output_path)

@router.post("/{document_id}/to-jpg")
async def pdf_to_jpg(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Convert a PDF document to JPG images (one per page)
    """
    document = db.query(Document).filter(Document.id == document_id, Document.owner_id == current_user.id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        storage_service = StorageService()
        local_file_path = storage_service.get_file(document.file_path)
        output_dir = tempfile.mkdtemp()
        try:
            image_paths = pdf_processor.pdf_to_jpg(local_file_path, output_dir)
            if not image_paths:
                raise HTTPException(
                    status_code=500,
                    detail="No images were generated from the PDF"
                )
            
            download_urls = []
            filenames = []
            for img_path in image_paths:
                # Upload to storage
                storage_path = storage_service.upload_file(img_path, os.path.basename(img_path))
                # Create a new document record for each image
                doc = Document(
                    filename=os.path.basename(img_path),
                    original_filename=os.path.basename(img_path),
                    file_path=storage_path,
                    file_size=os.path.getsize(img_path),
                    mime_type="image/jpeg",
                    file_type="jpg",
                    owner_id=current_user.id
                )
                db.add(doc)
                db.commit()
                db.refresh(doc)
                
                # Add download URL and filename
                download_urls.append(f"/documents/{doc.id}/download")
                filenames.append(doc.filename)
            
            return {
                "download_urls": download_urls,
                "filenames": filenames,
                "page_count": len(image_paths)
            }
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)
    except FileNotFoundError as e:
        logger.error(f"File not found for document {document_id}: {str(e)}")
        # Delete the orphaned database record
        db.delete(document)
        db.commit()
        logger.info(f"Deleted orphaned document record: {document_id}")
        raise HTTPException(
            status_code=404,
            detail="The original file is no longer available. The document record has been cleaned up. Please upload the file again."
        )
    except Exception as e:
        logger.error(f"Error in pdf_to_jpg: {str(e)}")
        if "poppler" in str(e).lower():
            raise HTTPException(
                status_code=503,
                detail="PDF to JPG conversion is currently unavailable. The required Poppler dependency is not installed. Please contact the administrator."
            )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to convert PDF to JPG: {str(e)}"
        )

@router.post("/convert/word-to-pdf", response_model=DocumentOperationResponse)
async def word_to_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Convert Word document to PDF"""
    # Validate file type
    allowed_extensions = ['.docx', '.doc', '.rtf', '.odt']
    allowed_mime_types = [
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
        'application/msword',  # .doc
        'application/rtf',  # .rtf
        'application/vnd.oasis.opendocument.text',  # .odt
        'text/rtf'  # .rtf alternative
    ]
    validate_file_type(file, allowed_extensions, allowed_mime_types)
    
    try:
        # Create a temporary file for the input
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_input:
            content = await file.read()
            temp_input.write(content)
            temp_input.flush()
            
            # Create a temporary file for the output
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_output:
                # Get LibreOffice path using the same logic as pdf_operations.py
                if os.name == 'nt':  # Windows
                    libreoffice_paths = [
                        r"C:\Program Files\LibreOffice\program\soffice.exe",
                        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
                        os.path.expanduser("~\\AppData\\Local\\Programs\\LibreOffice\\program\\soffice.exe")
                    ]
                    soffice_path = None
                    for path in libreoffice_paths:
                        if os.path.exists(path):
                            soffice_path = path
                            break
                else:  # Linux/Mac
                    linux_paths = [
                        "/usr/bin/libreoffice",
                        "/usr/bin/soffice",
                        "/usr/lib/libreoffice/program/soffice",
                        "/opt/libreoffice/program/soffice",
                        "/snap/bin/libreoffice",
                        "/usr/local/bin/libreoffice",
                        "/usr/local/bin/soffice"
                    ]
                    soffice_path = None
                    for path in linux_paths:
                        if os.path.exists(path):
                            soffice_path = path
                            break
                    if not soffice_path:
                        try:
                            soffice_path = subprocess.check_output(['which', 'libreoffice']).decode().strip()
                        except Exception as e:
                            logger.error(f"Error finding libreoffice: {str(e)}")
                            try:
                                soffice_path = subprocess.check_output(['which', 'soffice']).decode().strip()
                            except Exception as e:
                                logger.error(f"Error finding soffice: {str(e)}")
                                raise FileNotFoundError("LibreOffice not found. Please install LibreOffice to use this feature.")

                if not soffice_path:
                    raise FileNotFoundError("LibreOffice not found. Please install LibreOffice to use this feature.")

                # Convert using LibreOffice
                result = subprocess.run([
                    soffice_path,
                    '--headless',
                    '--convert-to', 'pdf',
                    '--outdir', os.path.dirname(temp_output.name),
                    temp_input.name
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Conversion failed: {result.stderr}"
                    )
                
                # Get the converted file path
                converted_file = os.path.join(
                    os.path.dirname(temp_output.name),
                    os.path.splitext(os.path.basename(temp_input.name))[0] + '.pdf'
                )
                
                if not os.path.exists(converted_file):
                    raise HTTPException(
                        status_code=500,
                        detail="Converted file not found"
                    )
                
                # Move the converted file to our output location
                shutil.move(converted_file, temp_output.name)
                
                # Create document record with owner
                doc = Document(
                    filename=f"{os.path.splitext(file.filename)[0]}_{uuid.uuid4()}.pdf",
                    original_filename=file.filename,
                    file_type="pdf",
                    conversion_type="word_to_pdf",
                    owner_id=current_user.id
                )
                db.add(doc)
                db.commit()
                db.refresh(doc)
                
                try:
                    # Verify the temp file exists and has content
                    if not os.path.exists(temp_output.name):
                        raise HTTPException(status_code=500, detail="Temporary output file was not created")
                    
                    if os.path.getsize(temp_output.name) == 0:
                        raise HTTPException(status_code=500, detail="Temporary output file is empty")
                    
                    # Upload the file using the filename only - storage service will handle the path
                    storage_service = StorageService()
                    file_path = storage_service.upload_file(temp_output.name, doc.filename)
                    print(f"Word to PDF conversion - storage service returned: {file_path}")
                    
                    # Update document with storage path
                    doc.file_path = file_path
                    db.commit()
                    db.refresh(doc)
                    print(f"Word to PDF conversion - saved to database with file_path: {doc.file_path}")
                    
                    # Construct the download URL with the correct API path
                    download_url = f"/documents/{doc.id}/download"
                    
                    return DocumentOperationResponse(
                        id=doc.id,
                        filename=doc.filename,
                        content_type="application/pdf",
                        created_at=doc.created_at,
                        download_url=download_url,
                        message="Word document converted successfully"
                    )
                except Exception as e:
                    # If storage upload fails, delete the document record
                    db.delete(doc)
                    db.commit()
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to upload converted file to storage: {str(e)}"
                    )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temporary files
        if 'temp_input' in locals():
            os.unlink(temp_input.name)
        if 'temp_output' in locals():
            os.unlink(temp_output.name)

@router.post("/convert/excel-to-pdf", response_model=DocumentOperationResponse)
async def excel_to_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Convert Excel document to PDF"""
    # Validate file type
    allowed_extensions = ['.xlsx', '.xls', '.ods', '.csv']
    allowed_mime_types = [
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
        'application/vnd.ms-excel',  # .xls
        'application/vnd.oasis.opendocument.spreadsheet',  # .ods
        'text/csv',  # .csv
        'application/csv'  # .csv alternative
    ]
    validate_file_type(file, allowed_extensions, allowed_mime_types)
    
    try:
        # Create a temporary file for the input
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_input:
            content = await file.read()
            temp_input.write(content)
            temp_input.flush()
            
            # Create a temporary file for the output
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_output:
                # Get LibreOffice path using the same logic as pdf_operations.py
                if os.name == 'nt':  # Windows
                    libreoffice_paths = [
                        r"C:\Program Files\LibreOffice\program\soffice.exe",
                        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
                        os.path.expanduser("~\\AppData\\Local\\Programs\\LibreOffice\\program\\soffice.exe")
                    ]
                    soffice_path = None
                    for path in libreoffice_paths:
                        if os.path.exists(path):
                            soffice_path = path
                            break
                else:  # Linux/Mac
                    linux_paths = [
                        "/usr/bin/libreoffice",
                        "/usr/bin/soffice",
                        "/usr/lib/libreoffice/program/soffice",
                        "/opt/libreoffice/program/soffice",
                        "/snap/bin/libreoffice",
                        "/usr/local/bin/libreoffice",
                        "/usr/local/bin/soffice"
                    ]
                    soffice_path = None
                    for path in linux_paths:
                        if os.path.exists(path):
                            soffice_path = path
                            break
                    if not soffice_path:
                        try:
                            soffice_path = subprocess.check_output(['which', 'libreoffice']).decode().strip()
                        except Exception as e:
                            logger.error(f"Error finding libreoffice: {str(e)}")
                            try:
                                soffice_path = subprocess.check_output(['which', 'soffice']).decode().strip()
                            except Exception as e:
                                logger.error(f"Error finding soffice: {str(e)}")
                                raise FileNotFoundError("LibreOffice not found. Please install LibreOffice to use this feature.")

                if not soffice_path:
                    raise FileNotFoundError("LibreOffice not found. Please install LibreOffice to use this feature.")

                # Convert using LibreOffice
                result = subprocess.run([
                    soffice_path,
                    '--headless',
                    '--convert-to', 'pdf',
                    '--outdir', os.path.dirname(temp_output.name),
                    temp_input.name
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Conversion failed: {result.stderr}"
                    )
                
                # Get the converted file path
                converted_file = os.path.join(
                    os.path.dirname(temp_output.name),
                    os.path.splitext(os.path.basename(temp_input.name))[0] + '.pdf'
                )
                
                if not os.path.exists(converted_file):
                    raise HTTPException(
                        status_code=500,
                        detail="Converted file not found"
                    )
                
                # Move the converted file to our output location
                shutil.move(converted_file, temp_output.name)
                
                # Create document record with owner
                doc = Document(
                    filename=f"{os.path.splitext(file.filename)[0]}_{uuid.uuid4()}.pdf",
                    original_filename=file.filename,
                    file_type="pdf",
                    conversion_type="excel_to_pdf",
                    owner_id=current_user.id
                )
                db.add(doc)
                db.commit()
                db.refresh(doc)
                
                try:
                    # Verify the temp file exists and has content
                    if not os.path.exists(temp_output.name):
                        raise HTTPException(status_code=500, detail="Temporary output file was not created")
                    
                    if os.path.getsize(temp_output.name) == 0:
                        raise HTTPException(status_code=500, detail="Temporary output file is empty")
                    
                    # Upload the file using the filename only - storage service will handle the path
                    storage_service = StorageService()
                    file_path = storage_service.upload_file(temp_output.name, doc.filename)
                    
                    # Update document with storage path
                    doc.file_path = file_path
                    db.commit()
                    db.refresh(doc)
                    
                    # Construct the download URL with the correct API path
                    download_url = f"/documents/{doc.id}/download"
                    
                    return DocumentOperationResponse(
                        id=doc.id,
                        filename=doc.filename,
                        content_type="application/pdf",
                        created_at=doc.created_at,
                        download_url=download_url,
                        message="Excel document converted successfully"
                    )
                except Exception as e:
                    # If storage upload fails, delete the document record
                    db.delete(doc)
                    db.commit()
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to upload converted file to storage: {str(e)}"
                    )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temporary files
        if 'temp_input' in locals():
            os.unlink(temp_input.name)
        if 'temp_output' in locals():
            os.unlink(temp_output.name)

@router.post("/convert/ppt-to-pdf", response_model=DocumentOperationResponse)
async def ppt_to_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Convert PowerPoint document to PDF"""
    # Validate file type
    allowed_extensions = ['.pptx', '.ppt', '.odp']
    allowed_mime_types = [
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # .pptx
        'application/vnd.ms-powerpoint',  # .ppt
        'application/vnd.oasis.opendocument.presentation'  # .odp
    ]
    validate_file_type(file, allowed_extensions, allowed_mime_types)
    
    try:
        # Create a temporary file for the input
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pptx') as temp_input:
            content = await file.read()
            temp_input.write(content)
            temp_input.flush()
            
            # Create a temporary file for the output
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_output:
                # Get LibreOffice path using the same logic as pdf_operations.py
                if os.name == 'nt':  # Windows
                    libreoffice_paths = [
                        r"C:\Program Files\LibreOffice\program\soffice.exe",
                        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
                        os.path.expanduser("~\\AppData\\Local\\Programs\\LibreOffice\\program\\soffice.exe")
                    ]
                    soffice_path = None
                    for path in libreoffice_paths:
                        if os.path.exists(path):
                            soffice_path = path
                            break
                else:  # Linux/Mac
                    linux_paths = [
                        "/usr/bin/libreoffice",
                        "/usr/bin/soffice",
                        "/usr/lib/libreoffice/program/soffice",
                        "/opt/libreoffice/program/soffice",
                        "/snap/bin/libreoffice",
                        "/usr/local/bin/libreoffice",
                        "/usr/local/bin/soffice"
                    ]
                    soffice_path = None
                    for path in linux_paths:
                        if os.path.exists(path):
                            soffice_path = path
                            break
                    if not soffice_path:
                        try:
                            soffice_path = subprocess.check_output(['which', 'libreoffice']).decode().strip()
                        except Exception as e:
                            logger.error(f"Error finding libreoffice: {str(e)}")
                            try:
                                soffice_path = subprocess.check_output(['which', 'soffice']).decode().strip()
                            except Exception as e:
                                logger.error(f"Error finding soffice: {str(e)}")
                                raise FileNotFoundError("LibreOffice not found. Please install LibreOffice to use this feature.")

                if not soffice_path:
                    raise FileNotFoundError("LibreOffice not found. Please install LibreOffice to use this feature.")

                # Convert using LibreOffice
                result = subprocess.run([
                    soffice_path,
                    '--headless',
                    '--convert-to', 'pdf',
                    '--outdir', os.path.dirname(temp_output.name),
                    temp_input.name
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Conversion failed: {result.stderr}"
                    )
                
                # Get the converted file path
                converted_file = os.path.join(
                    os.path.dirname(temp_output.name),
                    os.path.splitext(os.path.basename(temp_input.name))[0] + '.pdf'
                )
                
                if not os.path.exists(converted_file):
                    raise HTTPException(
                        status_code=500,
                        detail="Converted file not found"
                    )
                
                # Move the converted file to our output location
                shutil.move(converted_file, temp_output.name)
                
                # Create document record with owner
                doc = Document(
                    filename=f"{os.path.splitext(file.filename)[0]}_{uuid.uuid4()}.pdf",
                    original_filename=file.filename,
                    file_type="pdf",
                    conversion_type="ppt_to_pdf",
                    owner_id=current_user.id
                )
                db.add(doc)
                db.commit()
                db.refresh(doc)
                
                try:
                    # Verify the temp file exists and has content
                    if not os.path.exists(temp_output.name):
                        raise HTTPException(status_code=500, detail="Temporary output file was not created")
                    
                    if os.path.getsize(temp_output.name) == 0:
                        raise HTTPException(status_code=500, detail="Temporary output file is empty")
                    
                    # Upload the file using the filename only - storage service will handle the path
                    storage_service = StorageService()
                    file_path = storage_service.upload_file(temp_output.name, doc.filename)
                    
                    # Update document with storage path
                    doc.file_path = file_path
                    db.commit()
                    db.refresh(doc)
                    
                    # Construct the download URL with the correct API path
                    download_url = f"/documents/{doc.id}/download"
                    
                    return DocumentOperationResponse(
                        id=doc.id,
                        filename=doc.filename,
                        content_type="application/pdf",
                        created_at=doc.created_at,
                        download_url=download_url,
                        message="PowerPoint document converted successfully"
                    )
                except Exception as e:
                    # If storage upload fails, delete the document record
                    db.delete(doc)
                    db.commit()
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to upload converted file to storage: {str(e)}"
                    )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temporary files
        if 'temp_input' in locals():
            os.unlink(temp_input.name)
        if 'temp_output' in locals():
            os.unlink(temp_output.name)

@router.get("/{document_id}/preview")
async def get_document_preview(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    response: Response = None
):
    """
    Get a preview image of the first page of a PDF document.
    Returns a JPEG image with caching headers.
    """
    document = db.query(Document).filter(Document.id == document_id, Document.owner_id == current_user.id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    try:
        # Get the file from storage
        storage_service = StorageService()
        local_file_path = storage_service.get_file(document.file_path)
        
        # Open the PDF
        pdf_document = fitz.open(local_file_path)
        
        # Get the first page
        first_page = pdf_document[0]
        
        # Convert to image with higher resolution (2x for better quality)
        pix = first_page.get_pixmap(matrix=fitz.Matrix(2, 2))
        
        # Convert to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Resize to thumbnail size while maintaining aspect ratio
        max_size = (400, 400)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Convert to bytes with good quality
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=85, optimize=True)
        img_byte_arr.seek(0)
        
        # Close the PDF
        pdf_document.close()
        
        # Set cache headers (1 hour cache)
        response.headers["Cache-Control"] = "public, max-age=3600"
        response.headers["ETag"] = f'"{document.id}-{document.last_accessed.timestamp()}"'
        
        return Response(
            content=img_byte_arr.getvalue(),
            media_type="image/jpeg"
        )
    except FileNotFoundError as e:
        logger.error(f"File not found for document {document_id}: {str(e)}")
        # Delete the orphaned database record
        db.delete(document)
        db.commit()
        logger.info(f"Deleted orphaned document record: {document_id}")
        raise HTTPException(
            status_code=404,
            detail="The file is no longer available. The document record has been cleaned up. Please upload the file again."
        )
    except Exception as e:
        logger.error(f"Error generating preview: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate preview"
        )


# PDF Editing Endpoints
@router.post("/{document_id}/edit-text", response_model=DocumentOperationResponse)
async def edit_text(
    document_id: str,
    page_number: int = Form(...),
    old_text: str = Form(...),
    new_text: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Edit text on a specific page of a PDF document.
    """
    try:
        storage_service = StorageService()
        
        # Get the document
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.owner_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Get the file path
        file_path = storage_service.get_file(document.file_path)
        
        # Create output path
        output_filename = f"{document.filename}_edited_{int(time.time())}.pdf"
        output_path = os.path.join(tempfile.gettempdir(), output_filename)
        
        # Edit the text
        PDFProcessor().edit_text_on_page(file_path, output_path, page_number, old_text, new_text)
        
        # Upload the edited file
        new_file_url = storage_service.upload_file(output_path, output_filename)
        
        # Create new document record
        new_document = Document(
            filename=output_filename,
            original_filename=document.original_filename,
            file_path=new_file_url,
            file_size=os.path.getsize(output_path),
            mime_type=document.mime_type,
            file_type=document.file_type,
            conversion_type="text_edit",
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            file_hash=None,
            owner_id=current_user.id
        )
        
        db.add(new_document)
        db.commit()
        db.refresh(new_document)
        
        # Clean up temp file
        os.unlink(output_path)
        
        return DocumentOperationResponse(
            success=True,
            message="Text edited successfully",
            new_document_id=new_document.id,
            download_url=f"/api/v1/documents/{new_document.id}/download"
        )
        
    except Exception as e:
        logger.error(f"Error editing text: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to edit text: {str(e)}"
        )


@router.post("/{document_id}/add-text", response_model=DocumentOperationResponse)
async def add_text(
    document_id: str,
    page_number: int = Form(...),
    text: str = Form(...),
    x: float = Form(...),
    y: float = Form(...),
    font_size: int = Form(12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Add text to a specific position on a page of a PDF document.
    """
    try:
        # Get the document
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.owner_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Get the file path
        file_path = storage_service.get_file(document.file_path)
        
        # Create output path
        output_filename = f"{document.filename}_added_text_{int(time.time())}.pdf"
        output_path = os.path.join(tempfile.gettempdir(), output_filename)
        
        # Add the text
        PDFProcessor().add_text_to_page(file_path, output_path, page_number, text, (x, y), font_size)
        
        # Upload the edited file
        new_file_url = storage_service.upload_file(output_path, output_filename)
        
        # Create new document record
        new_document = Document(
            filename=output_filename,
            original_filename=document.original_filename,
            file_path=new_file_url,
            file_size=os.path.getsize(output_path),
            mime_type=document.mime_type,
            file_type=document.file_type,
            conversion_type="add_text",
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            file_hash=None,
            owner_id=current_user.id
        )
        
        db.add(new_document)
        db.commit()
        db.refresh(new_document)
        
        # Clean up temp file
        os.unlink(output_path)
        
        return DocumentOperationResponse(
            success=True,
            message="Text added successfully",
            new_document_id=new_document.id,
            download_url=f"/api/v1/documents/{new_document.id}/download"
        )
        
    except Exception as e:
        logger.error(f"Error adding text: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add text: {str(e)}"
        )


@router.post("/{document_id}/remove-images", response_model=DocumentOperationResponse)
async def remove_images(
    document_id: str,
    page_number: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Remove all images from a specific page of a PDF document.
    """
    try:
        # Get the document
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.owner_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Get the file path
        file_path = storage_service.get_file(document.file_path)
        
        # Create output path
        output_filename = f"{document.filename}_no_images_{int(time.time())}.pdf"
        output_path = os.path.join(tempfile.gettempdir(), output_filename)
        
        # Remove images
        PDFProcessor().remove_images_from_page(file_path, output_path, page_number)
        
        # Upload the edited file
        new_file_url = storage_service.upload_file(output_path, output_filename)
        
        # Create new document record
        new_document = Document(
            filename=output_filename,
            original_filename=document.original_filename,
            file_path=new_file_url,
            file_size=os.path.getsize(output_path),
            mime_type=document.mime_type,
            file_type=document.file_type,
            conversion_type="remove_images",
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            file_hash=None,
            owner_id=current_user.id
        )
        
        db.add(new_document)
        db.commit()
        db.refresh(new_document)
        
        # Clean up temp file
        os.unlink(output_path)
        
        return DocumentOperationResponse(
            success=True,
            message="Images removed successfully",
            new_document_id=new_document.id,
            download_url=f"/api/v1/documents/{new_document.id}/download"
        )
        
    except Exception as e:
        logger.error(f"Error removing images: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove images: {str(e)}"
        )


@router.post("/{document_id}/annotate", response_model=DocumentOperationResponse)
async def annotate(
    document_id: str,
    page_number: int = Form(...),
    annotation_type: str = Form(...),
    data: str = Form(...),  # JSON string
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Add annotations (highlight, comment, draw) to a page of a PDF document.
    """
    try:
        import json
        
        # Get the document
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.owner_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Parse annotation data
        try:
            annotation_data = json.loads(data)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid annotation data format"
            )
        
        # Get the file path
        file_path = storage_service.get_file(document.file_path)
        
        # Create output path
        output_filename = f"{document.filename}_annotated_{int(time.time())}.pdf"
        output_path = os.path.join(tempfile.gettempdir(), output_filename)
        
        # Add annotation
        PDFProcessor().annotate_page(file_path, output_path, page_number, annotation_type, annotation_data)
        
        # Upload the edited file
        new_file_url = storage_service.upload_file(output_path, output_filename)
        
        # Create new document record
        new_document = Document(
            filename=output_filename,
            original_filename=document.original_filename,
            file_path=new_file_url,
            file_size=os.path.getsize(output_path),
            mime_type=document.mime_type,
            file_type=document.file_type,
            conversion_type="annotate",
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            file_hash=None,
            owner_id=current_user.id
        )
        
        db.add(new_document)
        db.commit()
        db.refresh(new_document)
        
        # Clean up temp file
        os.unlink(output_path)
        
        return DocumentOperationResponse(
            success=True,
            message="Annotation added successfully",
            new_document_id=new_document.id,
            download_url=f"/api/v1/documents/{new_document.id}/download"
        )
        
    except Exception as e:
        logger.error(f"Error adding annotation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add annotation: {str(e)}"
        )


@router.post("/{document_id}/reorder-pages", response_model=DocumentOperationResponse)
async def reorder_pages(
    document_id: str,
    new_order: str = Form(...),  # JSON string
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Reorder pages of a PDF document.
    """
    try:
        import json
        
        # Get the document
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.owner_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Parse new_order JSON string
        try:
            new_order_list = json.loads(new_order)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid page order format"
            )
        
        # Get the file path
        file_path = storage_service.get_file(document.file_path)
        
        # Create output path
        output_filename = f"{document.filename}_reordered_{int(time.time())}.pdf"
        output_path = os.path.join(tempfile.gettempdir(), output_filename)
        
        # Reorder pages
        PDFProcessor().reorder_pages(file_path, output_path, new_order_list)
        
        # Upload the edited file
        new_file_url = storage_service.upload_file(output_path, output_filename)
        
        # Create new document record
        new_document = Document(
            filename=output_filename,
            original_filename=document.original_filename,
            file_path=new_file_url,
            file_size=os.path.getsize(output_path),
            mime_type=document.mime_type,
            file_type=document.file_type,
            conversion_type="reorder_pages",
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            file_hash=None,
            owner_id=current_user.id
        )
        
        db.add(new_document)
        db.commit()
        db.refresh(new_document)
        
        # Clean up temp file
        os.unlink(output_path)
        
        return DocumentOperationResponse(
            success=True,
            message="Pages reordered successfully",
            new_document_id=new_document.id,
            download_url=f"/api/v1/documents/{new_document.id}/download"
        )
        
    except Exception as e:
        logger.error(f"Error reordering pages: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reorder pages: {str(e)}"
        )