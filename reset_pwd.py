import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Database configuration
POSTGRES_SERVER = "localhost"
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "sammyokay"
POSTGRES_DB = "redanpdf"

# Create database URL
SQLALCHEMY_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}/{POSTGRES_DB}"

# Create engine and session
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def reset_password(email: str, new_password: str):
    db = SessionLocal()
    try:
        # Get user
        result = db.execute(text("SELECT id FROM users WHERE email = :email"), {"email": email})
        user = result.fetchone()
        
        if not user:
            print(f"User with email {email} not found")
            return False
        
        # Hash new password
        hashed_password = get_password_hash(new_password)
        
        # Update password
        db.execute(
            text("UPDATE users SET hashed_password = :hashed_password WHERE email = :email"),
            {"hashed_password": hashed_password, "email": email}
        )
        db.commit()
        print(f"Password reset successful for {email}")
        return True
    except Exception as e:
        print(f"Error resetting password: {str(e)}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    email = "sammyokorie0@gmail.com"
    new_password = "newpassword123"
    reset_password(email, new_password) 