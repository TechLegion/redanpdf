from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from typing import Optional
import logging

from pdf_saas_app.app.db.session import Base
from pdf_saas_app.app.core.pdf_operations import PDFProcessor
from pdf_saas_app.app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True, default=generate_uuid)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    documents = relationship("Document", back_populates="owner")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, index=True, default=generate_uuid)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)  # Original uploaded filename
    file_path = Column(String)  # URL or path to stored file
    file_size = Column(Integer)  # Size in bytes
    mime_type = Column(String)
    file_type = Column(String)  # Type of file (e.g., 'pdf', 'docx')
    conversion_type = Column(String)  # Type of conversion (e.g., 'word_to_pdf')
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    
    owner_id = Column(String, ForeignKey("users.id"))
    owner = relationship("User", back_populates="documents")
    
    chat_history = relationship("ChatHistory", back_populates="document")
    
    def get_text_content(self) -> Optional[str]:
        """Extract text content on-demand"""
        try:
            storage_service = StorageService()
            local_file_path = storage_service.get_file(self.file_path)
            pdf_processor = PDFProcessor()
            return pdf_processor.extract_text(local_file_path)
        except FileNotFoundError as e:
            logger.error(f"File not found for text extraction: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error extracting text content: {str(e)}")
            return None

class ChatHistory(Base):
    __tablename__ = "chat_history"
    
    id = Column(String, primary_key=True, index=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.id"))
    user_id = Column(String, ForeignKey("users.id"))
    query = Column(Text)
    response = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    document = relationship("Document", back_populates="chat_history")

class PDF(Base):
    __tablename__ = "pdfs"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    file_path = Column(String, nullable=False)