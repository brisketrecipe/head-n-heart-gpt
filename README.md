# Educational Content Management System

An AI-powered system for managing and retrieving educational content with automated tagging and intelligent search capabilities.

## Features

- Document processing for various file types (PDF, DOCX, TXT, Images)
- Automated content tagging using GPT-3.5
- Vector-based semantic search using Pinecone
- Intelligent content retrieval with RAG (Retrieval Augmented Generation)
- Google Cloud Storage integration for file management

## Project Structure

```
.
├── backend/
│   ├── app.py                 # FastAPI application
│   ├── document_processor.py  # Document parsing and chunking
│   ├── auto_tagger.py        # Automated tagging system
│   ├── vector_store.py       # Pinecone integration
│   ├── storage_service.py    # Google Cloud Storage integration
│   ├── query_engine.py       # RAG implementation
│   └── requirements.txt      # Python dependencies
├── frontend/
│   ├── src/                  # React components
│   └── public/              # Static assets
└── scripts/
    └── setup.py             # Initial setup script
```

## Setup

1. Clone the repository
2. Install backend dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Fill in your API keys and configuration

4. Required services:
   - OpenAI API key
   - Pinecone account and API key
   - Google Cloud Storage bucket and credentials

## Running the Application

1. Start the backend server:
   ```bash
   cd backend
   uvicorn app:app --reload
   ```

2. The API will be available at `http://localhost:8000`

## API Endpoints

- `POST /upload`: Upload and process a document
- `POST /query`: Search for content with optional filters
- `GET /health`: Health check endpoint

## Tag Categories

The system uses four main categories for content tagging:

1. Action
   - Lecture, Assignment, Reading, Exercise, Quiz, etc.

2. Relationships
   - Student-Led, Group Work, Prerequisite, Follow-up, etc.

3. Discipline
   - Mathematics, Biology, Computer Science, Literature, etc.

4. Purpose
   - Conceptual Understanding, Skill Building, Assessment, etc.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License 