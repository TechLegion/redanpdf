# PDF SaaS API

A FastAPI-based SaaS backend for PDF management with AI and OCR capabilities. Supports user authentication, PDF upload, listing, download, deletion, merging, watermarking, compressing, image-to-PDF conversion, and AI-powered features (chat, summarization, grammar check). Now includes OCR for scanned/image-based PDFs.

---

## Features
- User registration and authentication (JWT)
- Upload, list, download, and delete PDF documents
- Merge, compress, and watermark PDFs
- Convert images to PDF
- Extract text from both digital and scanned PDFs (OCR-ready)
- **Pure OCR endpoint:** Extract text from PDFs using only Tesseract (no OpenAI required)
- AI features: chat with PDF, summarization, grammar check (if configured)
- Local, S3, or Azure storage support
- Automated and manual testing

---

## Setup Instructions

### 1. Clone the Repository
```bash
# Clone and enter the project directory
cd PDFelement
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install Tesseract OCR Engine
- **Windows:** [Download here](https://github.com/tesseract-ocr/tesseract/wiki) and add to PATH
- **Ubuntu/Debian:**
  ```bash
  sudo apt update && sudo apt install tesseract-ocr
  ```
- **macOS:**
  ```bash
  brew install tesseract
  ```

### 4. Configure Environment Variables
Create a `.env` file with your settings (see `app/config.py` for required variables):
```
STORAGE_TYPE=local
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=yourpassword
POSTGRES_DB=pdf_db
# ...and any other required settings
```

### 5. Run the Application
```bash
uvicorn app.main:app --reload
# or
python -m app.main
```

### 6. Access the API
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Dummy Frontend:** Open `test_frontend.html` in your browser

---

## Main API Endpoints

### Authentication
- `POST /api/v1/auth/register` — Register
- `POST /api/v1/auth/token` — Login (get JWT)
- `GET /api/v1/auth/me` — Get current user

### PDF Management
- `POST /api/v1/documents/upload` — Upload PDF
- `GET /api/v1/documents/list` — List PDFs
- `GET /api/v1/documents/{document_id}` — Download PDF
- `DELETE /api/v1/documents/{document_id}` — Delete PDF
- `POST /api/v1/documents/merge` — Merge PDFs
- `POST /api/v1/documents/{document_id}/watermark` — Add watermark
- `POST /api/v1/documents/{document_id}/compress` — **Compress a PDF**
- `POST /api/v1/documents/image-to-pdf` — **Convert images to PDF**
- `GET /api/v1/documents/{document_id}/extract-text` — **Extract text (with OCR) from a PDF using only Tesseract**

### AI Features (if enabled)
- `POST /api/v1/ai/chat` — Chat with PDF
- `POST /api/v1/ai/summarize/{document_id}` — Summarize PDF
- `POST /api/v1/ai/grammar-check` — Grammar check

### Health
- `GET /health` — Health check

---

## Notes
- **OCR:** The app will extract text from scanned/image PDFs using Tesseract OCR. Use the `/api/v1/documents/{document_id}/extract-text` endpoint for pure OCR (no OpenAI required).
- **PDF Manipulation:** Merge, compress, and image-to-PDF features are available and testable from the dummy frontend and Swagger UI.
- **Storage:** By default, files are stored locally. You can switch to S3 or Azure by updating your `.env` and config.
- **Testing:**
  - Run all tests: `pytest -v`
  - Dummy frontend (`test_frontend.html`) allows manual testing of all main features, including pure OCR extraction, merge, compress, and image-to-PDF.
- **Production:** For deployment, use a production server (e.g., Gunicorn + Uvicorn), set up a managed DB, and use cloud storage as needed.

---

## License
MIT