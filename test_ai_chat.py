#!/usr/bin/env python3
"""
Script to test AI chat functionality with authentication
"""
import requests
import json
import sys

# API base URL
BASE_URL = "http://localhost:8000/api/v1"

def login_user(email, password):
    """Login and get authentication token"""
    login_data = {
        "username": email,
        "password": password
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/token", data=login_data)
        if response.status_code == 200:
            token_data = response.json()
            return token_data.get("access_token")
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def test_ai_chat(token, query):
    """Test AI chat endpoint"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    chat_data = {
        "query": query
    }
    
    try:
        response = requests.post(f"{BASE_URL}/ai/chat", headers=headers, json=chat_data)
        if response.status_code == 200:
            chat_response = response.json()
            return chat_response
        else:
            print(f"❌ AI chat failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ AI chat error: {e}")
        return None

def test_grammar_check(token, text):
    """Test grammar check endpoint"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    grammar_data = {
        "text": text
    }
    
    try:
        response = requests.post(f"{BASE_URL}/ai/grammar-check", headers=headers, json=grammar_data)
        if response.status_code == 200:
            grammar_response = response.json()
            return grammar_response
        else:
            print(f"❌ Grammar check failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Grammar check error: {e}")
        return None

def main():
    print("🤖 Testing AI Chat Functionality")
    print("=" * 50)
    
    # Login
    print("🔐 Logging in...")
    token = login_user("sammyokorie0@gmail.com", "sammyokay")
    
    if not token:
        print("❌ Failed to get authentication token")
        return False
    
    print("✅ Login successful!")
    print(f"🔑 Token: {token[:20]}...")
    
    # Test AI Chat
    print("\n💬 Testing AI Chat...")
    chat_response = test_ai_chat(token, "Hello! Can you help me understand what this PDF is about?")
    
    if chat_response:
        print("✅ AI Chat working!")
        print(f"🤖 Response: {chat_response.get('response', 'No response')}")
    else:
        print("❌ AI Chat failed")
    
    # Test Grammar Check
    print("\n📝 Testing Grammar Check...")
    grammar_response = test_grammar_check(token, "This is a test sentance with some grammer errors.")
    
    if grammar_response:
        print("✅ Grammar Check working!")
        print(f"📝 Corrected: {grammar_response.get('corrected_text', 'No correction')}")
    else:
        print("❌ Grammar Check failed")
    
    print("\n🎉 AI Chat testing completed!")
    return True

if __name__ == "__main__":
    main()
