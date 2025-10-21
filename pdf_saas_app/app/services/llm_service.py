import openai
from langchain_community.llms import OpenAI as LangchainOpenAI
from langchain.chains.summarize import load_summarize_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from typing import List, Optional, Dict, Any
import json

from pdf_saas_app.app.config import settings
from pdf_saas_app.app.core.pdf_operations import PDFProcessor

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
        Summarize document content using LangChain
        
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
        docs = [Document(page_content=t) for t in texts]
        
        # Use LangChain for summarization
        llm = LangchainOpenAI(temperature=0, openai_api_key=settings.OPENAI_API_KEY)
        chain = load_summarize_chain(llm, chain_type="map_reduce")
        summary = chain.run(docs)
        
        # If the summary is too long, make a final summarization pass
        if len(summary) > max_length:
            summary_doc = [Document(page_content=summary)]
            summary = chain.run(summary_doc)
        
        return summary
    
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