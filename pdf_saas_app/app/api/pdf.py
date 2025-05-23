from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Response
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services import pdf_services
import shutil
import os

router = APIRouter(prefix="/pdfs", tags=["PDFs"])

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
def download_pdf(pdf_id: int, db: Session = Depends(get_db)):
    pdf = pdf_services.get_pdf(db, pdf_id)
    if not pdf or not os.path.exists(pdf.file_path):
        raise HTTPException(status_code=404, detail="PDF not found")
    with open(pdf.file_path, "rb") as f:
        return Response(content=f.read(), media_type="application/pdf")

@router.delete("/{pdf_id}")
def delete_pdf(pdf_id: int, db: Session = Depends(get_db)):
    success = pdf_services.delete_pdf(db, pdf_id)
    if not success:
        raise HTTPException(status_code=404, detail="PDF not found")
    return {"detail": "PDF deleted"} 