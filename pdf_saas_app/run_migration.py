#!/usr/bin/env python3
"""
Migration runner script for Docker container
This script handles the Python path and runs the database migration
"""

import os
import sys
import subprocess

def main():
    """Run database migration with proper Python path"""
    print("🚀 Starting PDF SaaS Application...")
    
    # Set up Python path
    app_dir = "/app/pdf_saas_app"
    os.chdir(app_dir)
    
    # Add the app directory to Python path
    sys.path.insert(0, app_dir)
    
    print("📊 Running database migrations...")
    
    try:
        # Run alembic upgrade with proper environment
        env = os.environ.copy()
        env['PYTHONPATH'] = f"{app_dir}:{env.get('PYTHONPATH', '')}"
        
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            env=env,
            cwd=app_dir,
            check=True,
            capture_output=True,
            text=True
        )
        
        print("✅ Database migrations completed successfully!")
        print(result.stdout)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed: {e}")
        print(f"Error output: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
