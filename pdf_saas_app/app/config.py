# This file will be populated with configuration settings 
import os
from typing import Any, Dict, Optional
from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "PDF SaaS API"
    
    # SECURITY
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # DATABASE
    # Prefer a single DATABASE_URL if provided; fall back to individual POSTGRES_* parts
    DATABASE_URL: Optional[str] = None
    POSTGRES_SERVER: Optional[str] = None
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None
    # Keep this as a generic string (not PostgresDsn) so any SQLAlchemy-supported backend works
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    # AI Services
    OPENAI_API_KEY: str

    # Storage
    STORAGE_TYPE: str = "local"  # local, s3, azure
    S3_BUCKET_NAME: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AZURE_CONNECTION_STRING: Optional[str] = None
    AZURE_CONTAINER_NAME: Optional[str] = None
    LOCAL_STORAGE_PATH: str = "storage"

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""
    FRONTEND_URL: str = "http://localhost:5500/pdf_saas_app/frontend/index.html"  # Optional, for redirect
    EXTRA: str = "allow"

    # Redis Configuration
    REDIS_URL: Optional[str] = None
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100  # requests per window
    RATE_LIMIT_WINDOW: int = 3600   # 1 hour window
    
    # Caching
    CACHE_ENABLED: bool = True
    CACHE_DEFAULT_TTL: int = 3600   # 1 hour default TTL

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        # 1) If explicitly provided, respect it
        if isinstance(v, str) and v:
            return v

        # 2) If DATABASE_URL is provided, use it directly
        database_url = values.data.get("DATABASE_URL")
        if isinstance(database_url, str) and database_url:
            return database_url

        # 3) Fallback: construct from POSTGRES_* parts if available
        pg_user = values.data.get("POSTGRES_USER")
        pg_password = values.data.get("POSTGRES_PASSWORD")
        pg_host = values.data.get("POSTGRES_SERVER")
        pg_db = values.data.get("POSTGRES_DB")

        if all([pg_user, pg_password, pg_host, pg_db]):
            return PostgresDsn.build(
                scheme="postgresql+psycopg",
                username=pg_user,
                password=pg_password,
                host=pg_host,
                path=f"{pg_db}",
                query="client_encoding=utf8"
            )

        # 4) As a last resort, leave it None; the app should error clearly if DB URL is missing
        return None

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="allow")


settings = Settings()