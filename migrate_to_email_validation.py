#!/usr/bin/env python3
"""
Migration script to switch from user ID to email validation for file access.
This script will:
1. Add an owner_email column to the documents table
2. Populate it with emails from the users table
3. Update the application code to use email validation
4. Ensure backward compatibility during transition
"""

import os
import sys
import psycopg
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'pdf_saas_app'))

from pdf_saas_app.app.config import settings

def get_database_connection():
    """Get database connection"""
    # Use the same connection string from your app
    DATABASE_URL = "postgresql://postgres:zGrHwADbJjnTskEqbKBUlpbTthpSynme@maglev.proxy.rlwy.net:38814/railway"
    return psycopg.connect(DATABASE_URL)

def migrate_database_schema():
    """Add owner_email column to documents table"""
    print("🔄 Adding owner_email column to documents table...")
    
    conn = get_database_connection()
    try:
        with conn.cursor() as cur:
            # Add the new column
            cur.execute("""
                ALTER TABLE documents 
                ADD COLUMN IF NOT EXISTS owner_email VARCHAR(255);
            """)
            
            # Create index for better performance
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_owner_email 
                ON documents(owner_email);
            """)
            
            conn.commit()
            print("✅ Successfully added owner_email column and index")
            
    except Exception as e:
        print(f"❌ Error adding column: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def populate_owner_emails():
    """Populate owner_email column with data from users table"""
    print("🔄 Populating owner_email column...")
    
    conn = get_database_connection()
    try:
        with conn.cursor() as cur:
            # Update documents with owner emails
            cur.execute("""
                UPDATE documents 
                SET owner_email = u.email 
                FROM users u 
                WHERE documents.owner_id = u.id;
            """)
            
            updated_count = cur.rowcount
            conn.commit()
            print(f"✅ Updated {updated_count} documents with owner emails")
            
    except Exception as e:
        print(f"❌ Error populating emails: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def verify_migration():
    """Verify the migration was successful"""
    print("🔍 Verifying migration...")
    
    conn = get_database_connection()
    try:
        with conn.cursor() as cur:
            # Check if column exists
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'documents' 
                AND column_name = 'owner_email';
            """)
            
            if cur.fetchone():
                print("✅ owner_email column exists")
            else:
                print("❌ owner_email column not found")
                return False
            
            # Check data integrity
            cur.execute("""
                SELECT 
                    COUNT(*) as total_docs,
                    COUNT(owner_email) as docs_with_email,
                    COUNT(owner_id) as docs_with_id
                FROM documents;
            """)
            
            result = cur.fetchone()
            print(f"📊 Migration stats:")
            print(f"   Total documents: {result[0]}")
            print(f"   Documents with email: {result[1]}")
            print(f"   Documents with ID: {result[2]}")
            
            # Check for any orphaned documents
            cur.execute("""
                SELECT COUNT(*) 
                FROM documents d 
                LEFT JOIN users u ON d.owner_id = u.id 
                WHERE u.id IS NULL;
            """)
            
            orphaned_count = cur.fetchone()[0]
            if orphaned_count > 0:
                print(f"⚠️  Found {orphaned_count} orphaned documents (no matching user)")
            else:
                print("✅ No orphaned documents found")
            
            return True
            
    except Exception as e:
        print(f"❌ Error verifying migration: {e}")
        return False
    finally:
        conn.close()

def create_backup():
    """Create a backup of the documents table before migration"""
    print("💾 Creating backup of documents table...")
    
    conn = get_database_connection()
    try:
        with conn.cursor() as cur:
            # Create backup table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS documents_backup AS 
                SELECT * FROM documents;
            """)
            conn.commit()
            print("✅ Backup created: documents_backup table")
            
    except Exception as e:
        print(f"❌ Error creating backup: {e}")
        raise
    finally:
        conn.close()

def main():
    """Run the complete migration"""
    print("🚀 Starting migration to email-based validation...")
    print("=" * 60)
    
    try:
        # Step 1: Create backup
        create_backup()
        
        # Step 2: Add new column
        migrate_database_schema()
        
        # Step 3: Populate data
        populate_owner_emails()
        
        # Step 4: Verify migration
        if verify_migration():
            print("\n🎉 Migration completed successfully!")
            print("\nNext steps:")
            print("1. Update your application code to use email validation")
            print("2. Test the new system")
            print("3. Once confirmed working, you can drop the owner_id column if desired")
        else:
            print("\n❌ Migration verification failed!")
            
    except Exception as e:
        print(f"\n💥 Migration failed: {e}")
        print("The backup table 'documents_backup' contains your original data")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
