# Use a more stable Python image
FROM python:3.11-bullseye

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Install essential packages for PDF processing
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install LibreOffice for document conversion
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

# Install minimal GUI libraries for PDF operations
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libxrender1 \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

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

# Make the startup script executable
RUN chmod +x /app/pdf_saas_app/start.sh

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

# Start the app with our startup script
CMD ["/app/pdf_saas_app/start.sh"] 