# Use an official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies (Tesseract, libgl for pdf2image, etc.)
RUN apt-get update && \
    apt-get install -y \
    tesseract-ocr \
    libgl1-mesa-glx \
    poppler-utils \
    wget \
    xz-utils \
    libglib2.0-0 \
    libxrender1 \
    libsm6 \
    libxext6 \
    libreoffice \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    fonts-liberation \
    libfontconfig1 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    libnss3 \
    libcups2 \
    libxshmfence1 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libpangocairo-1.0-0 \
    libgtk-3-0 \
    libgbm1 \
    calibre && \
    # Clean up
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create a non-root user
RUN useradd -m -u 1000 appuser

# Set work directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Set proper permissions
RUN chown -R appuser:appuser /app && \
    chmod -R 755 /app

# Create necessary directories with proper permissions
RUN mkdir -p /app/storage && \
    chown -R appuser:appuser /app/storage && \
    chmod -R 755 /app/storage

# Switch to non-root user
USER appuser

# Expose the port FastAPI will run on
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the app with Uvicorn
CMD ["uvicorn", "pdf_saas_app.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--timeout-keep-alive", "120", "--limit-concurrency", "1000"] 