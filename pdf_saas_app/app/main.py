from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
from pdf_saas_app.app.api import auth, documents, ai_chat, auth_google
from pdf_saas_app.app.db.session import engine, Base
from pdf_saas_app.app.config import settings
from starlette.middleware.sessions import SessionMiddleware

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

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY
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

# Include Google auth router with a different prefix
app.include_router(
    auth_google.router,
    prefix=f"{settings.API_V1_STR}/auth/google",
    tags=["authentication"]
)

@app.get("/")
async def root():
    return {
        "message": "Welcome to PDF SaaS API, Currently Redanpdf",
        "View the documentation at": "/docs",
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/debug/db")
def debug_db():
    return {
        "POSTGRES_DB": settings.POSTGRES_DB,
        "SQLALCHEMY_DATABASE_URI": str(settings.SQLALCHEMY_DATABASE_URI)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("pdf_saas_app.app.main:app", host="0.0.0.0", port=8000, reload=True)