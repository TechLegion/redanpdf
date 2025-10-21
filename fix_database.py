#!/usr/bin/env python3
"""
Script to fix the database schema by adding missing columns
"""
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pdf_saas_app.app.db.session import engine
from sqlalchemy import text

def fix_database():
    """Add missing columns to the database"""
    try:
        with engine.connect() as conn:
            # Add file_hash column if it doesn't exist
            try:
                conn.execute(text('ALTER TABLE documents ADD COLUMN file_hash VARCHAR;'))
                conn.commit()
                print("✅ Successfully added file_hash column")
            except Exception as e:
                if "already exists" in str(e) or "duplicate column" in str(e).lower():
                    print("ℹ️  file_hash column already exists")
                else:
                    print(f"⚠️  Error adding file_hash column: {e}")
            
            # Add index for file_hash if it doesn't exist
            try:
                conn.execute(text('CREATE INDEX IF NOT EXISTS ix_documents_file_hash ON documents (file_hash);'))
                conn.commit()
                print("✅ Successfully added file_hash index")
            except Exception as e:
                print(f"ℹ️  Index might already exist: {e}")
                
        print("🎉 Database schema fix completed!")
        
    except Exception as e:
        print(f"❌ Error fixing database: {e}")
        return False
    
    return True

if __name__ == "__main__":
    fix_database()
