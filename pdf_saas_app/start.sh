#!/bin/bash

# Startup script for Docker container
# This script runs database migrations and starts the FastAPI application

set -e  # Exit on any error

echo "🚀 Starting PDF SaaS Application..."

# Change to the app directory
cd /app/pdf_saas_app

echo "📊 Running database migrations..."
# Run Alembic migrations
alembic upgrade head

echo "✅ Database migrations completed successfully!"

echo "🌐 Starting FastAPI application..."
# Start the application
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --timeout-keep-alive 120 --limit-concurrency 1000
