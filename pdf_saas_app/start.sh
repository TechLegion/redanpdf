#!/bin/bash

# Startup script for Docker container
# This script starts the FastAPI application

echo "🚀 Starting PDF SaaS Application..."

# Change to the app directory
cd /app/pdf_saas_app

# Add the current directory to Python path
export PYTHONPATH="/app/pdf_saas_app:$PYTHONPATH"

echo "🌐 Starting FastAPI application..."
# Start the application
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --timeout-keep-alive 120 --limit-concurrency 1000
