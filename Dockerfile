# Use an official Python image
FROM python:3.11-slim

# Install system dependencies (Tesseract, libgl for pdf2image, etc.)
RUN apt-get update && \
    apt-get install -y tesseract-ocr libgl1-mesa-glx poppler-utils wget xz-utils libglib2.0-0 libxrender1 libsm6 libxext6 && \
    # Install Calibre (headless)
    wget -nv -O- https://download.calibre-ebook.com/linux-installer.sh | sh /dev/stdin && \
    rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose the port FastAPI will run on
EXPOSE 8000

# Start the app with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 