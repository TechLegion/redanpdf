import openai
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from typing import List, Optional, Dict, Any
import json

from app.config import settings
from app.core.pdf_operations import PDFProcessor

class AIService:
    """Service for AI operations including chat, summarization, and grammar checking"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.pdf_processor = PDFProcessor()
    
    def generate_chat_response(self, user_query: str, context: Optional[str] = None) -> str:
        """
        Generate an AI response to a user query about a PDF
        
        Args:
            user_query: The user's question
            context: Optional text context from the PDF
        
        Returns:
            The AI response
        """
        messages = [
            {"role": "system", "content": "You are a helpful PDF assistant."}
        ]
        
        if context:
            # Include PDF context if available
            messages.append({
                "role": "system", 
                "content": f"Here is the relevant content from the PDF document: {context}"
            })
        
        messages.append({"role": "user", "content": user_query})
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=messages
        )
        
        return response.choices[0].message.content
    
    def summarize_document(self, text_content: str, max_length: int = 1000) -> str:
        """
        Summarize document content using direct OpenAI API with chunking
        
        Args:
            text_content: The text content to summarize
            max_length: Maximum length of the summary in characters
        
        Returns:
            The summarized text
        """
        # Create text chunks for processing
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=100
        )
        texts = text_splitter.split_text(text_content)
        
        # If we have multiple chunks, summarize each chunk first
        if len(texts) > 1:
            chunk_summaries = []
            for chunk in texts:
                chunk_summary = self._summarize_chunk(chunk, max_length // len(texts))
                chunk_summaries.append(chunk_summary)
            
            # Combine chunk summaries and summarize again
            combined_text = " ".join(chunk_summaries)
            final_summary = self._summarize_chunk(combined_text, max_length)
        else:
            # Single chunk, summarize directly
            final_summary = self._summarize_chunk(texts[0], max_length)
        
        return final_summary
    
    def _summarize_chunk(self, text: str, max_length: int) -> str:
        """Helper method to summarize a single chunk of text"""
        # Truncate text if it's too long for the API
        if len(text) > 12000:  # Leave room for prompt
            text = text[:12000]
        
        prompt = f"""
        Please summarize the following text in a clear and concise manner. 
        The summary should be no more than {max_length} characters.
        
        Text to summarize:
        {text}
        
        Summary:
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that creates clear and concise summaries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content.strip()
            
            # If summary is still too long, truncate it
            if len(summary) > max_length:
                summary = summary[:max_length] + "..."
            
            return summary
            
        except Exception as e:
            return f"Error generating summary: {str(e)}"
    
    def check_grammar(self, text: str) -> Dict[str, Any]:
        """
        Check grammar and spelling in text
        
        Args:
            text: The text to check for grammar and spelling errors
        
        Returns:
            Dictionary with corrected text and list of corrections
        """
        system_prompt = """
        You are a professional grammar and spell checker. Analyze the text for grammar and spelling errors.
        Provide the corrected text as well as a list of all corrections made.
        Format your response as JSON with the following structure:
        {
            "corrected_text": "The full corrected text",
            "corrections": [
                {"original": "original text", "corrected": "corrected text", "explanation": "brief explanation"},
                ...
            ]
        }
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ]
        )
        
        try:
            result = json.loads(response.choices[0].message.content)
            return result
        except json.JSONDecodeError:
            # Fallback in case JSON parsing fails
            return {
                "corrected_text": response.choices[0].message.content,
                "corrections": []
            }