# PDF SaaS API

A comprehensive PDF processing backend built with FastAPI, featuring AI-powered capabilities including chatbot, grammar checking, and document summarization.

## Features

- **PDF Operations**: Upload, merge, split, rotate, watermark and more
- **AI Features**:
  - Chat with PDFs using AI
  - Document summarization
  - Grammar checking
- **User Authentication**: JWT-based authentication
- **Storage Options**: Local, S3, or Azure Blob Storage
- **Database**: PostgreSQL for document and user management
- **Containerized**: Docker and Docker Compose ready

## Tech Stack

- **FastAPI**: Modern, high-performance web framework for building APIs
- **SQLAlchemy**: ORM for database interactions
- **PyMuPDF & PyPDF2**: PDF processing libraries
- **OpenAI API & LangChain**: AI and language model integration
- **Docker**: Containerization
- **Redis**: Caching and rate limiting
- **PostgreSQL**: SQL database

## Prerequisites

- Python 3.11+
- Docker and Docker Compose (optional but recommended)
- OpenAI API key

## Setup & Installation

### Using Docker (Recommended)

1. Clone the repository
   ```bash
   git clone https://github.com/TechLegion/pdf-saas-api.git
   cd pdf-saas-api
   ```

2. Create a `.env` file based on `.env.example`
   ```bash
   cp .env.example .env
   ```

3. Update the `.env` file with your OpenAI API key and other settings

4. Start the services using Docker Compose
   ```bash
   docker-compose up -d
   ```

5. Access the API at http://localhost:8000 and API documentation at http://localhost:8000/docs

### Manual Setup

1. Clone the repository and navigate to the directory
   ```bash
   git clone https://github.com/yourusername/pdf-saas-api.git
   cd pdf-saas-api
   ```

2. Create a virtual environment and activate it
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file based on `.env.example` and update with your settings

5. Set up the database
   ```bash
   # Make sure PostgreSQL is running and accessible
   # The application will create tables automatically
   ```

6. Run the application
   ```bash
   uvicorn app.main:app --reload
   ```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register a new user
- `POST /api/v1/auth/token` - Get access token
- `GET /api/v1/auth/me` - Get current user info

### Document Operations
- `POST /api/v1/documents/upload` - Upload a PDF document
- `GET /api/v1/documents/list` - List all documents
- `GET /api/v1/documents/{document_id}` - Get a document
- `POST /api/v1/documents/merge` - Merge multiple documents
- `POST /api/v1/documents/{document_id}/watermark` - Add watermark to a document
- `DELETE /api/v1/documents/{document_id}` - Delete a document

### AI Features
- `POST /api/v1/ai/chat` - Chat with AI about PDF content
- `POST /api/v1/ai/summarize/{document_id}` - Summarize a document
- `POST /api/v1/ai/grammar-check` - Check grammar in text

## Development

### Project Structure

```
pdf-saas-api/
├── app/                    # Main application package
│   ├── api/                # API endpoints
│   ├── core/               # Core business logic
│   ├── db/                 # Database models and connection
│   ├── services/           # External services integration
│   ├── utils/              # Utility functions
│   ├── config.py           # Configuration
│   └── main.py             # Application entry point
├── tests/                  # Test suite
├── storage/                # Local storage for files
├── .env                    # Environment variables
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker configuration
└── docker-compose.yml      # Docker Compose configuration
```

### Running Tests

```bash
pytest
```

## License

[MIT License](LICENSE)