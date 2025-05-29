from fastapi import APIRouter, Depends, HTTPException, Body, status
from sqlalchemy.orm import Session
from typing import Dict, Optional
from pydantic import BaseModel

from pdf_saas_app.app.db.session import get_db
from pdf_saas_app.app.db.models import User, Document, ChatHistory
from pdf_saas_app.app.services.auth_services import get_current_active_user
from pdf_saas_app.app.services.llm_service import AIService

router = APIRouter()
ai_service = AIService()

class ChatRequest(BaseModel):
    query: str
    document_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: Optional[str] = None

class SummarizeResponse(BaseModel):
    summary: str

class GrammarRequest(BaseModel):
    text: str

class GrammarResponse(BaseModel):
    corrected_text: str
    corrections: list

@router.post("/chat", response_model=ChatResponse)
async def chat_with_pdf(
    chat_request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Chat with AI about PDF content
    """
    context = None
    document = None
    
    if chat_request.document_id:
        # Get document context if a document ID is provided
        document = db.query(Document).filter(
            Document.id == chat_request.document_id,
            Document.owner_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Use the extracted text content
        context = document.text_content
    
    # Generate AI response
    response = ai_service.generate_chat_response(chat_request.query, context)
    
    # Save chat history if a document was referenced
    conversation_id = None
    if document:
        chat_history = ChatHistory(
            document_id=document.id,
            user_id=current_user.id,
            query=chat_request.query,
            response=response
        )
        db.add(chat_history)
        db.commit()
        db.refresh(chat_history)
        conversation_id = chat_history.id
    
    return {
        "response": response,
        "conversation_id": conversation_id
    }

@router.post("/summarize/{document_id}", response_model=SummarizeResponse)
async def summarize_document(
    document_id: str,
    max_length: Optional[int] = 1000,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Summarize PDF content
    """
    # Get document
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.owner_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Use the text content we extracted at upload time
    if not document.text_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text content available for this document"
        )
    
    # Generate summary
    summary = ai_service.summarize_document(document.text_content, max_length)
    
    return {"summary": summary}

@router.post("/grammar-check", response_model=GrammarResponse)
async def check_grammar(
    request: GrammarRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Check grammar and spelling in text
    """
    result = ai_service.check_grammar(request.text)
    return result