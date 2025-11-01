from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
from app.api import auth, documents, ai_chat, auth_google, pdf
from app.db.session import engine, Base
from app.config import settings
from app.services.redis_service import redis_service
from starlette.middleware.sessions import SessionMiddleware

# Create database tables if they don't exist (lazy initialization)
def init_database():
    """Initialize database tables on startup"""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Warning: Database initialization failed: {e}")
        print("Application will continue, but database operations may fail.")

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
    allow_origins=[
        "*",  # Allow all origins for development
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "https://redanpdf-kz99.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY
)

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_database()

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

app.include_router(
    pdf.router,
    prefix=f"{settings.API_V1_STR}/pdfs",
    tags=["pdf-edit"]
)

@app.get("/")
async def root():
    return {
        "message": "Welcome to PDF SaaS API, Currently Redanpdf",
        "View the documentation at": "/docs",
    }

@app.get("/health")
async def health_check():
    """Enhanced health check including Redis status"""
    health_status = {
        "status": "healthy",
        "services": {
            "database": "healthy",
            "storage": "healthy",
            "redis": "unavailable"
        }
    }
    
    # Check Redis health
    try:
        redis_health = redis_service.health_check()
        health_status["services"]["redis"] = redis_health["status"]
        
        if redis_health["status"] == "error":
            health_status["status"] = "degraded"
            health_status["redis_error"] = redis_health.get("error", "Unknown error")
    except Exception as e:
        health_status["services"]["redis"] = "error"
        health_status["redis_error"] = str(e)
    
    return health_status

@app.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics"""
    from app.utils.cache import CacheManager
    return CacheManager.get_cache_stats()

@app.get("/cache/clear")
async def clear_cache():
    """Clear all cache (admin endpoint)"""
    if redis_service.is_available():
        # Clear all cache keys (use with caution)
        deleted_count = redis_service.clear_cache_pattern("*")
        return {"message": f"Cleared {deleted_count} cache entries"}
    else:
        return {"message": "Redis not available"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)