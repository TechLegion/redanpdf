#!/bin/bash

# Startup script for Docker container
# This script runs database migrations and starts the FastAPI application

# Don't exit on error - allow app to start even if migration fails

echo "🚀 Starting PDF SaaS Application..."

# Change to the app directory
cd /app/pdf_saas_app

# Add the current directory to Python path
export PYTHONPATH="/app/pdf_saas_app:$PYTHONPATH"

echo "📊 Running database migrations..."
# Run migration using Python script
python run_migration.py

echo "🌐 Starting FastAPI application..."
# Start the application
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --timeout-keep-alive 120 --limit-concurrency 1000
