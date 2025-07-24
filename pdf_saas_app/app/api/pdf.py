from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Response
from sqlalchemy.orm import Session
from pdf_saas_app.app.db.session import get_db
from pdf_saas_app.app.services import pdf_services
import shutil
import os
from pdf_saas_app.app.core.pdf_operations import PDFProcessor
from pdf_saas_app.app.db.models import Document
from pdf_saas_app.app.services.storage_service import StorageService

router = APIRouter(prefix="/pdfs", tags=["PDFs"])

storage_service = StorageService()

@router.post("/upload")
def upload_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_location = os.path.join(pdf_services.PDF_STORAGE_DIR, file.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    pdf = pdf_services.save_pdf(db, filename=file.filename, file_path=file_location)
    return {"id": pdf.id, "filename": pdf.filename}

@router.get("/")
def list_pdfs(db: Session = Depends(get_db)):
    pdfs = pdf_services.list_pdfs(db)
    return [{"id": pdf.id, "filename": pdf.filename, "upload_date": pdf.upload_date} for pdf in pdfs]

@router.get("/{pdf_id}")
def download_pdf(pdf_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == pdf_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="PDF not found")
    try:
        file_path = storage_service.get_file(doc.file_path)
    except Exception:
        raise HTTPException(status_code=404, detail="PDF not found")
    with open(file_path, "rb") as f:
        return Response(content=f.read(), media_type="application/pdf")

@router.delete("/{pdf_id}")
def delete_pdf(pdf_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == pdf_id).first()
    if doc:
        storage_service.delete_file(doc.file_path)
        db.delete(doc)
        db.commit()
        return {"detail": "PDF deleted"}
    raise HTTPException(status_code=404, detail="PDF not found")

@router.post("/{pdf_id}/edit_text")
def edit_text(pdf_id: str, page_number: int, old_text: str, new_text: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == pdf_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="PDF not found")
    try:
        file_path = storage_service.get_file(doc.file_path)
    except Exception:
        raise HTTPException(status_code=404, detail="PDF not found")
    output_path = file_path + ".edited.pdf"
    PDFProcessor().edit_text_on_page(file_path, output_path, page_number, old_text, new_text)
    return {"detail": "Text edit stub called", "output_path": output_path}

@router.post("/{pdf_id}/add_text")
def add_text(pdf_id: str, page_number: int, text: str, x: float, y: float, font_size: int = 12, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == pdf_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="PDF not found")
    try:
        file_path = storage_service.get_file(doc.file_path)
    except Exception:
        raise HTTPException(status_code=404, detail="PDF not found")
    output_path = file_path + ".addtext.pdf"
    PDFProcessor().add_text_to_page(file_path, output_path, page_number, text, (x, y), font_size)
    return {"detail": "Add text stub called", "output_path": output_path}

@router.post("/{pdf_id}/add_image")
def add_image(pdf_id: str, page_number: int, image_path: str, x: float, y: float, width: float = None, height: float = None, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == pdf_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="PDF not found")
    try:
        file_path = storage_service.get_file(doc.file_path)
    except Exception:
        raise HTTPException(status_code=404, detail="PDF not found")
    output_path = file_path + ".addimage.pdf"
    size = (width, height) if width and height else None
    PDFProcessor().add_image_to_page(file_path, output_path, page_number, image_path, (x, y), size)
    return {"detail": "Add image stub called", "output_path": output_path}

@router.post("/{pdf_id}/remove_images")
def remove_images(pdf_id: str, page_number: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == pdf_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="PDF not found")
    try:
        file_path = storage_service.get_file(doc.file_path)
    except Exception:
        raise HTTPException(status_code=404, detail="PDF not found")
    output_path = file_path + ".noimages.pdf"
    PDFProcessor().remove_images_from_page(file_path, output_path, page_number)
    return {"detail": "Remove images stub called", "output_path": output_path}

@router.post("/{pdf_id}/annotate")
def annotate(pdf_id: str, page_number: int, annotation_type: str, data: dict, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == pdf_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="PDF not found")
    try:
        file_path = storage_service.get_file(doc.file_path)
    except Exception:
        raise HTTPException(status_code=404, detail="PDF not found")
    output_path = file_path + ".annotated.pdf"
    PDFProcessor().annotate_page(file_path, output_path, page_number, annotation_type, data)
    return {"detail": "Annotate stub called", "output_path": output_path}

@router.post("/{pdf_id}/reorder_pages")
def reorder_pages(pdf_id: str, new_order: list, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == pdf_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="PDF not found")
    try:
        file_path = storage_service.get_file(doc.file_path)
    except Exception:
        raise HTTPException(status_code=404, detail="PDF not found")
    output_path = file_path + ".reordered.pdf"
    PDFProcessor().reorder_pages(file_path, output_path, new_order)
    return {"detail": "Reorder pages stub called", "output_path": output_path} 