#!/usr/bin/env python3
"""
Test script to verify the email-based validation system works correctly
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'pdf_saas_app'))

from pdf_saas_app.app.db.session import get_db
from pdf_saas_app.app.db.models import User, Document
from pdf_saas_app.app.services.auth_services import get_password_hash
from sqlalchemy.orm import Session

def test_email_validation():
    """Test the email-based document access system"""
    
    print("🧪 Testing email-based validation system...")
    print("=" * 60)
    
    # Get database session
    db = next(get_db())
    
    try:
        # Test 1: Check if users exist
        users = db.query(User).all()
        print(f"📊 Found {len(users)} users in database")
        
        for user in users:
            print(f"   - {user.email} (ID: {user.id})")
        
        # Test 2: Create a test document with email validation
        if users:
            test_user = users[0]
            print(f"\n🔬 Testing with user: {test_user.email}")
            
            # Create a test document
            test_doc = Document(
                filename="test_document.pdf",
                original_filename="test_document.pdf",
                file_path="/test/path/test_document.pdf",
                file_size=1024,
                mime_type="application/pdf",
                file_type="pdf",
                owner_id=test_user.id,
                owner_email=test_user.email,
                file_hash="test_hash_123"
            )
            
            db.add(test_doc)
            db.commit()
            db.refresh(test_doc)
            
            print(f"✅ Created test document: {test_doc.id}")
            
            # Test 3: Query documents by email
            docs_by_email = db.query(Document).filter(Document.owner_email == test_user.email).all()
            print(f"📄 Found {len(docs_by_email)} documents for email: {test_user.email}")
            
            # Test 4: Query documents by ID (should still work)
            docs_by_id = db.query(Document).filter(Document.owner_id == test_user.id).all()
            print(f"📄 Found {len(docs_by_id)} documents for ID: {test_user.id}")
            
            # Test 5: Verify both queries return the same results
            if len(docs_by_email) == len(docs_by_id) == 1:
                print("✅ Email and ID queries return consistent results")
            else:
                print("❌ Inconsistent results between email and ID queries")
            
            # Test 6: Test access control simulation
            print(f"\n🔒 Testing access control...")
            
            # Simulate user accessing their own document
            user_docs = db.query(Document).filter(
                Document.id == test_doc.id,
                Document.owner_email == test_user.email
            ).first()
            
            if user_docs:
                print("✅ User can access their own document via email validation")
            else:
                print("❌ User cannot access their own document")
            
            # Simulate different user trying to access the document
            if len(users) > 1:
                other_user = users[1]
                other_user_docs = db.query(Document).filter(
                    Document.id == test_doc.id,
                    Document.owner_email == other_user.email
                ).first()
                
                if not other_user_docs:
                    print("✅ Other users cannot access documents they don't own")
                else:
                    print("❌ Security issue: Other users can access documents they don't own")
            
            # Clean up test document
            db.delete(test_doc)
            db.commit()
            print("🧹 Cleaned up test document")
            
        else:
            print("❌ No users found in database")
            
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        db.rollback()
        return False
    finally:
        db.close()
    
    print("\n🎉 Email-based validation test completed!")
    return True

if __name__ == "__main__":
    success = test_email_validation()
    sys.exit(0 if success else 1)
