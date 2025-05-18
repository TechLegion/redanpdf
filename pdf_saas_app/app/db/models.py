from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.session import Base

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
    filename = Column(String)
    file_path = Column(String)  # URL or path to stored file
    file_size = Column(Integer)  # Size in bytes
    mime_type = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    
    owner_id = Column(String, ForeignKey("users.id"))
    owner = relationship("User", back_populates="documents")
    
    # Extracted content for AI processing
    text_content = Column(Text, nullable=True)
    
    chat_history = relationship("ChatHistory", back_populates="document")
    
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