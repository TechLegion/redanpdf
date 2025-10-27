#!/usr/bin/env python3
"""
Local verification script for bcrypt password length fix
This script tests the password hashing functions locally
"""

import os
import sys

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'pdf_saas_app'))

def test_password_functions():
    """Test password hashing and verification functions"""
    print("🧪 Testing Password Functions Locally...")
    print("=" * 50)
    
    try:
        from pdf_saas_app.app.services.auth_services import get_password_hash, verify_password
        
        # Test cases with different password lengths
        test_cases = [
            ("short", 5),
            ("medium_length_password", 20),
            ("a" * 50, 50),
            ("a" * 72, 72),  # Exactly bcrypt limit
            ("a" * 100, 100),  # Exceeds bcrypt limit
            ("a" * 200, 200),  # Far exceeds bcrypt limit
            ("password_with_special_chars!@#$%^&*()_+-=[]{}|;':\",./<>?`~", 58),
            ("password with spaces and unicode: 你好世界 🌍", 40),
        ]
        
        all_passed = True
        
        for i, (password, expected_length) in enumerate(test_cases, 1):
            print(f"\nTest {i}: Password length {len(password)} chars (expected: {expected_length})")
            print(f"  Password: {password[:30]}{'...' if len(password) > 30 else ''}")
            
            try:
                # Test password hashing
                hashed = get_password_hash(password)
                print(f"  Hash: {hashed[:50]}...")
                
                # Test password verification
                is_valid = verify_password(password, hashed)
                print(f"  Verification: {'✅ PASS' if is_valid else '❌ FAIL'}")
                
                if not is_valid:
                    all_passed = False
                
                # Test with wrong password
                wrong_password = password + "wrong"
                is_invalid = verify_password(wrong_password, hashed)
                print(f"  Wrong password test: {'✅ PASS' if not is_invalid else '❌ FAIL'}")
                
                if is_invalid:
                    all_passed = False
                
            except Exception as e:
                print(f"  ❌ ERROR: {e}")
                all_passed = False
        
        return all_passed
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running from the correct directory and the app is properly set up.")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_bcrypt_specific():
    """Test bcrypt-specific functionality"""
    print("\n🔐 Testing Bcrypt-Specific Functionality...")
    print("=" * 50)
    
    try:
        from passlib.context import CryptContext
        
        # Test with bcrypt only
        bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Test long password with bcrypt
        long_password = "a" * 100
        print(f"Testing long password ({len(long_password)} chars) with bcrypt...")
        
        try:
            # This should fail with bcrypt
            hashed = bcrypt_context.hash(long_password)
            print("  ❌ Unexpected: bcrypt accepted long password")
            return False
        except ValueError as e:
            if "password cannot be longer than 72 bytes" in str(e):
                print("  ✅ Expected: bcrypt rejected long password")
            else:
                print(f"  ❌ Unexpected error: {e}")
                return False
        
        # Test with truncated password
        truncated_password = long_password[:72]
        print(f"Testing truncated password ({len(truncated_password)} chars) with bcrypt...")
        
        try:
            hashed = bcrypt_context.hash(truncated_password)
            is_valid = bcrypt_context.verify(truncated_password, hashed)
            print(f"  {'✅ PASS' if is_valid else '❌ FAIL'}: Truncated password works with bcrypt")
            return is_valid
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Bcrypt test failed: {e}")
        return False

def test_argon2_functionality():
    """Test argon2 functionality"""
    print("\n🔒 Testing Argon2 Functionality...")
    print("=" * 50)
    
    try:
        from passlib.context import CryptContext
        
        # Test with argon2
        argon2_context = CryptContext(schemes=["argon2"], deprecated="auto")
        
        # Test long password with argon2
        long_password = "a" * 200
        print(f"Testing long password ({len(long_password)} chars) with argon2...")
        
        try:
            hashed = argon2_context.hash(long_password)
            is_valid = argon2_context.verify(long_password, hashed)
            print(f"  {'✅ PASS' if is_valid else '❌ FAIL'}: Argon2 handles long passwords")
            return is_valid
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Argon2 test failed: {e}")
        return False

def main():
    """Main verification function"""
    print("🚀 Starting Local Verification Script...")
    print("=" * 60)
    
    # Run tests
    password_test = test_password_functions()
    bcrypt_test = test_bcrypt_specific()
    argon2_test = test_argon2_functionality()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    tests = [
        ("Password Functions", password_test),
        ("Bcrypt Functionality", bcrypt_test),
        ("Argon2 Functionality", argon2_test)
    ]
    
    for test_name, passed in tests:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    total_tests = len(tests)
    passed_tests = sum(passed for _, passed in tests)
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! The password fixes are working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
