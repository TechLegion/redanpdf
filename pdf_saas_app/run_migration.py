#!/usr/bin/env python3
"""
Migration runner script for Docker container
This script handles database migrations with proper error handling
"""

import os
import sys
import subprocess

def run_migration():
    """Run database migration with error handling"""
    try:
        print("🔄 Running database migration...")
        
        # Set up environment
        os.environ['PYTHONPATH'] = '/app/pdf_saas_app'
        
        # Run alembic migration
        result = subprocess.run(
            ['alembic', 'upgrade', 'head'],
            cwd='/app/pdf_saas_app',
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Database migration completed successfully!")
            return True
        else:
            print(f"❌ Migration failed with return code: {result.returncode}")
            print(f"Error output: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    if not success:
        print("⚠️  Migration failed, but continuing with startup...")
        print("   The application will still work, but some features may not be available")
    sys.exit(0)  # Always exit successfully to allow app to start