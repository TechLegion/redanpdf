from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from pdf_saas_app.app.db.models import User

# Database connection
DATABASE_URL = "postgresql://techlegion:ual9QE0NnaRQiAKkneOLxyg261lBxxw4@dpg-d0l4u1pr0fns73940s70-a.oregon-postgres.render.com/redanpdf_92v7"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def reset_password(email: str, new_password: str):
    db = SessionLocal()
    try:
        # Find user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"No user found with email: {email}")
            return False
        
        # Update password
        hashed_password = pwd_context.hash(new_password)
        user.hashed_password = hashed_password
        db.commit()
        print(f"Password successfully reset for user: {email}")
        return True
    except Exception as e:
        print(f"Error resetting password: {str(e)}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    email = input("Enter your email: ")
    new_password = input("Enter new password: ")
    reset_password(email, new_password) 