#!/usr/bin/env python3
"""
API verification script for the deployed application
This script tests the API endpoints to verify the fixes are working
"""

import requests
import json
import time
from typing import Dict, Any

def test_health_endpoint(base_url: str) -> bool:
    """Test if the application is running"""
    print("🏥 Testing Health Endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health endpoint is responding")
            return True
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")
        return False

def test_api_docs(base_url: str) -> bool:
    """Test if API documentation is accessible"""
    print("\n📚 Testing API Documentation...")
    try:
        response = requests.get(f"{base_url}/docs", timeout=10)
        if response.status_code == 200:
            print("✅ API documentation is accessible")
            return True
        else:
            print(f"❌ API documentation failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API documentation error: {e}")
        return False

def test_authentication(base_url: str) -> bool:
    """Test authentication with various password lengths"""
    print("\n🔐 Testing Authentication...")
    
    # Test credentials with different password lengths
    test_credentials = [
        {"username": "davidokoh@gmail.com", "password": "short", "description": "Short password"},
        {"username": "davidokoh@gmail.com", "password": "a" * 50, "description": "Medium password (50 chars)"},
        {"username": "davidokoh@gmail.com", "password": "a" * 100, "description": "Long password (100 chars)"},
        {"username": "davidokoh@gmail.com", "password": "Test1234!@#$%^&*()_+-=[]{}|;':\",./<>?`~", "description": "Special characters"},
    ]
    
    success_count = 0
    
    for i, creds in enumerate(test_credentials, 1):
        print(f"\n  Test {i}: {creds['description']} ({len(creds['password'])} chars)")
        
        try:
            # Test login
            response = requests.post(
                f"{base_url}/api/v1/auth/token",
                data=creds,
                timeout=15
            )
            
            if response.status_code == 200:
                token_data = response.json()
                print(f"    ✅ Login successful - Token received")
                
                # Test protected endpoint
                headers = {"Authorization": f"Bearer {token_data['access_token']}"}
                me_response = requests.get(
                    f"{base_url}/api/v1/auth/me",
                    headers=headers,
                    timeout=10
                )
                
                if me_response.status_code == 200:
                    user_data = me_response.json()
                    print(f"    ✅ Protected endpoint access - User: {user_data.get('email', 'Unknown')}")
                    success_count += 1
                else:
                    print(f"    ❌ Protected endpoint failed: {me_response.status_code}")
                    
            else:
                print(f"    ❌ Login failed: {response.status_code}")
                if response.text:
                    print(f"    Error details: {response.text[:200]}...")
                
        except requests.exceptions.Timeout:
            print(f"    ❌ Request timeout")
        except requests.exceptions.RequestException as e:
            print(f"    ❌ Network error: {e}")
        except Exception as e:
            print(f"    ❌ Unexpected error: {e}")
    
    print(f"\n  Authentication summary: {success_count}/{len(test_credentials)} tests passed")
    return success_count > 0

def test_document_endpoints(base_url: str, token: str) -> bool:
    """Test document-related endpoints"""
    print("\n📄 Testing Document Endpoints...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Test document list endpoint
        response = requests.get(
            f"{base_url}/api/v1/documents/list",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            documents = response.json()
            print(f"✅ Document list endpoint works - Found {len(documents)} documents")
            return True
        else:
            print(f"❌ Document list failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Document endpoint error: {e}")
        return False

def get_auth_token(base_url: str) -> str:
    """Get authentication token for testing"""
    try:
        response = requests.post(
            f"{base_url}/api/v1/auth/token",
            data={"username": "davidokoh@gmail.com", "password": "short"},
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            print(f"Failed to get auth token: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error getting auth token: {e}")
        return None

def main():
    """Main verification function"""
    print("🚀 Starting API Verification Script...")
    print("=" * 60)
    
    # Configuration
    BASE_URL = "https://redanpdf-kz99.onrender.com"
    
    # Test results
    results = {
        "health_endpoint": False,
        "api_docs": False,
        "authentication": False,
        "document_endpoints": False
    }
    
    # Run tests
    results["health_endpoint"] = test_health_endpoint(BASE_URL)
    results["api_docs"] = test_api_docs(BASE_URL)
    results["authentication"] = test_authentication(BASE_URL)
    
    # Test document endpoints if authentication works
    if results["authentication"]:
        token = get_auth_token(BASE_URL)
        if token:
            results["document_endpoints"] = test_document_endpoints(BASE_URL, token)
    
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
        print("🎉 All tests passed! The application is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
