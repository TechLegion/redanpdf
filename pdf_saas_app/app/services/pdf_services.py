from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.models import PDF
import os

PDF_STORAGE_DIR = os.path.join(os.path.dirname(__file__), '../static/pdfs')

# Ensure the storage directory exists
os.makedirs(PDF_STORAGE_DIR, exist_ok=True)

def save_pdf(db: Session, filename: str, file_path: str) -> PDF:
    pdf = PDF(filename=filename, file_path=file_path)
    db.add(pdf)
    db.commit()
    db.refresh(pdf)
    return pdf

def list_pdfs(db: Session) -> List[PDF]:
    return db.query(PDF).all()

def get_pdf(db: Session, pdf_id: int) -> Optional[PDF]:
    return db.query(PDF).filter(PDF.id == pdf_id).first()

def delete_pdf(db: Session, pdf_id: int) -> bool:
    pdf = db.query(PDF).filter(PDF.id == pdf_id).first()
    if pdf:
        db.delete(pdf)
        db.commit()
        # Optionally, remove the file from disk
        if os.path.exists(pdf.file_path):
            os.remove(pdf.file_path)
        return True
    return False 