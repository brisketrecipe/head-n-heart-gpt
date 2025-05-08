import logging
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from dotenv import load_dotenv
from datetime import datetime
import openai
from document_processor import DocumentProcessor
from openai_service import OpenAIService
from storage_service import StorageService
from pinecone_service import PineconeService

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
from pinecone_service import PineconeService

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
pinecone_service = PineconeService()

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
        
        # Generate embeddings for each chunk
        chunk_objs = []
        for chunk in chunks:
            embedding_response = openai_service.client.embeddings.create(
                input=chunk["text"] if isinstance(chunk, dict) and "text" in chunk else chunk,
                model="text-embedding-ada-002"
            )
            embedding = embedding_response.data[0].embedding
            chunk_objs.append({"text": chunk["text"] if isinstance(chunk, dict) and "text" in chunk else chunk, "embedding": embedding})
        
        # Upsert to Pinecone
        pinecone_service.upsert_chunks(filename, chunk_objs, tags)
        
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
        # Generate embedding for query
        query_embedding_response = openai_service.client.embeddings.create(
            input=query,
            model="text-embedding-ada-002"
        )
        query_embedding = query_embedding_response.data[0].embedding
        # Query Pinecone
        matches = pinecone_service.query(query_embedding, top_k=5)
        # Gather context from top chunks
        chunks = [match["metadata"]["chunkText"] for match in matches]
        context = "\n\n".join(chunks)
        # Use GPT-4o to answer
        response = openai_service.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
            ]
        )
        return {"reply": response.choices[0].message.content}
    except Exception as e:
        logging.exception("Error in /query endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"} 