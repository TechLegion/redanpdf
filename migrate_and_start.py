#!/usr/bin/env python3
"""
Migration and startup script for Render deployment
This script handles database migrations and starts the FastAPI application
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def run_command(command, cwd=None):
    """Run a command and return success status"""
    try:
        print(f"🔄 Running: {command}")
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd, 
            check=True, 
            capture_output=True, 
            text=True
        )
        print(f"✅ Success: {command}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running {command}: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False

def main():
    """Main migration and startup process"""
    print("🚀 Starting PDF SaaS Application Migration and Startup...")
    
    # Change to the app directory
    app_dir = Path("pdf_saas_app")
    if not app_dir.exists():
        print("❌ pdf_saas_app directory not found!")
        sys.exit(1)
    
    os.chdir(app_dir)
    print(f"📁 Changed to directory: {os.getcwd()}")
    
    # Step 1: Run database migrations
    print("\n📊 Running database migrations...")
    migration_success = run_command("alembic upgrade head")
    
    if not migration_success:
        print("⚠️  Migration failed, but continuing with startup...")
        print("   The application will still work, but some features may not be available")
    else:
        print("✅ Database migrations completed successfully!")
    
    # Step 2: Start the FastAPI application
    print("\n🌐 Starting FastAPI application...")
    port = os.environ.get("PORT", "8000")
    
    # Start the application
    try:
        subprocess.run([
            "uvicorn", 
            "app.main:app", 
            "--host", "0.0.0.0", 
            "--port", port
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start application: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user")
        sys.exit(0)

if __name__ == "__main__":
    main()
