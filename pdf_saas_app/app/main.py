from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os

from app.api import auth, documents, ai_chat
from app.db.session import engine, Base
from app.config import settings

# Create database tables if they don't exist
Base.metadata.create_all(bind=engine)

# Create storage directory if using local storage
if settings.STORAGE_TYPE == "local":
    os.makedirs(settings.LOCAL_STORAGE_PATH, exist_ok=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="PDF SaaS API with AI capabilities",
    version="1.0.0",
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["authentication"]
)

app.include_router(
    documents.router,
    prefix=f"{settings.API_V1_STR}/documents",
    tags=["documents"]
)

app.include_router(
    ai_chat.router,
    prefix=f"{settings.API_V1_STR}/ai",
    tags=["ai"]
)

@app.get("/")
async def root():
    return {
        "message": "Welcome to PDF SaaS API",
        "documentation": "/docs",
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)