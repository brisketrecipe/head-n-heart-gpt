import logging
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from dotenv import load_dotenv
from datetime import datetime

# Set up logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

# Import our components
from document_processor import DocumentProcessor
from openai_service import OpenAIService
from storage_service import StorageService

# Create FastAPI app
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
document_processor = DocumentProcessor()
openai_service = OpenAIService()
storage_service = StorageService(bucket_name=os.getenv("GCS_BUCKET_NAME"))

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        # Read file content
        content = await file.read()
        filename = file.filename
        
        # Process document content and detect type
        extracted_content, filetype = document_processor.extract_content(filename, content)
        
        # Process with OpenAI (chunking and tagging)
        chunks, tags = openai_service.process_document(extracted_content, filename, filetype=filetype)
        
        # Store in GCS
        gcs_path = storage_service.upload_file(content, filename)
        
        # Store processed results
        processed_data = {
            "filename": filename,
            "gcs_path": gcs_path,
            "chunks": chunks,
            "tags": tags,
            "processed_date": str(datetime.now())
        }
        
        # Store processed data in GCS
        storage_service.store_processed_content(filename, processed_data)
        
        return {
            "filename": filename,
            "chunks_processed": len(chunks),
            "tags": tags,
            "gcs_path": gcs_path
        }
    except Exception as e:
        logging.exception("Error in /upload endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def query_content(request: Request):
    try:
        data = await request.json()
        query = data.get("query", "")
        # Get all processed documents from storage
        processed_docs = []
        for filename in storage_service.list_processed():
            processed_docs.append(storage_service.get_processed(filename))
        # Pass to OpenAI service to search and generate response
        response = openai_service.search_content(query, processed_docs)
        return response
    except Exception as e:
        logging.exception("Error in /query endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"} 