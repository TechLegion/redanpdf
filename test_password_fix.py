#!/usr/bin/env python3
"""
Simple test to verify the password fix works
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'pdf_saas_app'))

def test_password_fix():
    """Test the improved password verification"""
    print("🧪 Testing Improved Password Verification...")
    print("=" * 50)
    
    try:
        from pdf_saas_app.app.services.auth_services import get_password_hash, verify_password
        
        # Test with a long password
        long_password = "a" * 100
        print(f"Testing password length: {len(long_password)} chars")
        
        # Hash the password
        hashed = get_password_hash(long_password)
        print(f"Hash generated: {hashed[:50]}...")
        
        # Verify with original password (should work with argon2)
        is_valid = verify_password(long_password, hashed)
        print(f"Verification with original password: {'✅ PASS' if is_valid else '❌ FAIL'}")
        
        # Test with wrong password
        wrong_password = long_password + "wrong"
        is_invalid = verify_password(wrong_password, hashed)
        print(f"Verification with wrong password: {'✅ PASS' if not is_invalid else '❌ FAIL'}")
        
        return is_valid and not is_invalid
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_password_fix()
    print(f"\n{'✅ Test passed!' if success else '❌ Test failed!'}")
    sys.exit(0 if success else 1)
