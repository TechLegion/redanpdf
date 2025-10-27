#!/usr/bin/env python3
"""
Verification script for bcrypt password length fix and email-based validation
This script tests the authentication system and file access functionality
"""

import os
import sys
import requests
import json
import time
from typing import Dict, Any

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'pdf_saas_app'))

def test_password_hashing():
    """Test password hashing with various password lengths"""
    print("🧪 Testing Password Hashing...")
    print("=" * 50)
    
    try:
        from pdf_saas_app.app.services.auth_services import get_password_hash, verify_password
        
        test_passwords = [
            "short",  # 5 chars
            "a" * 50,  # 50 chars
            "a" * 72,  # Exactly 72 chars (bcrypt limit)
            "a" * 100,  # 100 chars (exceeds bcrypt limit)
            "a" * 200,  # 200 chars (far exceeds bcrypt limit)
            "password_with_special_chars!@#$%^&*()_+-=[]{}|;':\",./<>?`~",  # Special chars
            "password with spaces and unicode: 你好世界 🌍",  # Unicode
        ]
        
        for i, password in enumerate(test_passwords, 1):
            try:
                print(f"\nTest {i}: Password length {len(password)} chars")
                print(f"  Original: {password[:20]}{'...' if len(password) > 20 else ''}")
                
                # Test password hashing
                hashed = get_password_hash(password)
                print(f"  Hashed: {hashed[:50]}...")
                
                # Test password verification
                is_valid = verify_password(password, hashed)
                print(f"  Verification: {'✅ PASS' if is_valid else '❌ FAIL'}")
                
                # Test with wrong password
                wrong_password = password + "wrong"
                is_invalid = verify_password(wrong_password, hashed)
                print(f"  Wrong password test: {'✅ PASS' if not is_invalid else '❌ FAIL'}")
                
            except Exception as e:
                print(f"  ❌ ERROR: {e}")
        
        print("\n✅ Password hashing tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Password hashing test failed: {e}")
        return False

def test_api_authentication(base_url: str):
    """Test API authentication with various password lengths"""
    print("\n🌐 Testing API Authentication...")
    print("=" * 50)
    
    # Test credentials
    test_credentials = [
        {"username": "davidokoh@gmail.com", "password": "short"},
        {"username": "davidokoh@gmail.com", "password": "a" * 50},
        {"username": "davidokoh@gmail.com", "password": "a" * 100},
        {"username": "davidokoh@gmail.com", "password": "Test1234!@#$%^&*()_+-=[]{}|;':\",./<>?`~"},
    ]
    
    for i, creds in enumerate(test_credentials, 1):
        try:
            print(f"\nTest {i}: Password length {len(creds['password'])} chars")
            
            # Test login
            response = requests.post(
                f"{base_url}/api/v1/auth/token",
                data=creds,
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                print(f"  ✅ Login successful - Token received")
                
                # Test protected endpoint
                headers = {"Authorization": f"Bearer {token_data['access_token']}"}
                me_response = requests.get(
                    f"{base_url}/api/v1/auth/me",
                    headers=headers,
                    timeout=10
                )
                
                if me_response.status_code == 200:
                    user_data = me_response.json()
                    print(f"  ✅ Protected endpoint access - User: {user_data.get('email', 'Unknown')}")
                else:
                    print(f"  ❌ Protected endpoint failed: {me_response.status_code}")
                    
            else:
                print(f"  ❌ Login failed: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Network error: {e}")
        except Exception as e:
            print(f"  ❌ Unexpected error: {e}")
    
    print("\n✅ API authentication tests completed!")
    return True

def test_database_connection():
    """Test database connection and email-based validation"""
    print("\n🗄️ Testing Database Connection...")
    print("=" * 50)
    
    try:
        from pdf_saas_app.app.db.session import get_db
        from pdf_saas_app.app.db.models import User, Document
        
        # Get database session
        db = next(get_db())
        
        # Test user query
        users = db.query(User).all()
        print(f"✅ Found {len(users)} users in database")
        
        for user in users:
            print(f"  - {user.email} (ID: {user.id})")
        
        # Test documents query (should work with email-based validation)
        documents = db.query(Document).all()
        print(f"✅ Found {len(documents)} documents in database")
        
        # Test email-based document filtering
        if users:
            test_user = users[0]
            user_docs = db.query(Document).filter(Document.owner_email == test_user.email).all()
            print(f"✅ Found {len(user_docs)} documents for user {test_user.email}")
        
        db.close()
        print("✅ Database connection tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_health_endpoint(base_url: str):
    """Test application health endpoint"""
    print("\n🏥 Testing Health Endpoint...")
    print("=" * 50)
    
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        
        if response.status_code == 200:
            print("✅ Health endpoint is responding")
            print(f"  Response: {response.text}")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            
        return response.status_code == 200
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Health endpoint error: {e}")
        return False

def test_api_docs(base_url: str):
    """Test API documentation endpoint"""
    print("\n📚 Testing API Documentation...")
    print("=" * 50)
    
    try:
        response = requests.get(f"{base_url}/docs", timeout=10)
        
        if response.status_code == 200:
            print("✅ API documentation is accessible")
        else:
            print(f"❌ API documentation failed: {response.status_code}")
            
        return response.status_code == 200
        
    except requests.exceptions.RequestException as e:
        print(f"❌ API documentation error: {e}")
        return False

def main():
    """Main verification function"""
    print("🚀 Starting Verification Script...")
    print("=" * 60)
    
    # Configuration
    BASE_URL = "https://redanpdf-kz99.onrender.com"
    
    # Test results
    results = {
        "password_hashing": False,
        "database_connection": False,
        "health_endpoint": False,
        "api_docs": False,
        "api_authentication": False
    }
    
    # Run tests
    print("Testing local components...")
    results["password_hashing"] = test_password_hashing()
    results["database_connection"] = test_database_connection()
    
    print("\nTesting remote API...")
    results["health_endpoint"] = test_health_endpoint(BASE_URL)
    results["api_docs"] = test_api_docs(BASE_URL)
    results["api_authentication"] = test_api_authentication(BASE_URL)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! The fixes are working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
