from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from pdf_saas_app.app.db.models import Base
from pdf_saas_app.app.config import Settings

# Database configuration
settings = Settings(
    POSTGRES_SERVER="localhost",
    POSTGRES_USER="postgres",
    POSTGRES_PASSWORD="sammyokay",
    POSTGRES_DB="redanpdf",
    SECRET_KEY="your-secret-key-here"
)

# Create database URL
SQLALCHEMY_DATABASE_URL = str(settings.SQLALCHEMY_DATABASE_URI)

# Create engine and session
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    init_db() 