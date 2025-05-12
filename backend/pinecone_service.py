import os
from pinecone import Pinecone
from dotenv import load_dotenv
import json

load_dotenv()

class PineconeService:
    def __init__(self):
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index_name = os.getenv("PINECONE_INDEX_NAME")
        # Auto-create index if it doesn't exist
        if index_name not in [i.name for i in self.pc.list_indexes()]:
            self.pc.create_index(
                name=index_name,
                dimension=1536,  # for OpenAI embeddings
                metric="cosine",
                spec={"serverless": {"cloud": "aws", "region": "us-east-1"}}
            )
        self.index = self.pc.Index(index_name)

    def upsert_chunks(self, filename, chunks, tags=None):
        """Store chunks in Pinecone with their associated tags"""
        vectors = []
        
        # Process each chunk
        for i, chunk in enumerate(chunks):
            # Extract chunk data
            chunk_id = chunk.get('chunk_id', f"{filename}-chunk-{i}")
            chunk_text = chunk.get('text', '')
            chunk_summary = chunk.get('summary', '')
            chunk_context = chunk.get('context', '')
            
            # Get the chunk's specific tags (should be embedded in the chunk)
            chunk_tags = chunk.get('tags', [])
            
            # If chunk has no tags but we have a global tags list (for backward compatibility)
            if not chunk_tags and tags and i < len(tags):
                chunk_tags = tags[i]
            
            # Convert tags to JSON string
            tags_json = json.dumps(chunk_tags)
            
            # Create the metadata for this chunk
            metadata = {
                "filename": filename,
                "chunkText": chunk_text,
                "chunkIndex": i,
                "chunkId": chunk_id,
                "summary": chunk_summary,
                "context": chunk_context,
                "tags": tags_json  # Store tags as JSON string
            }
            
            # Extract or create embedding
            embedding = chunk.get('embedding', None)
            
            # If no embedding, generate one
            if not embedding and hasattr(self, 'generate_embedding'):
                embedding = self.generate_embedding(chunk_text)
            
            # Only add vector if we have an embedding
            if embedding:
                vectors.append((chunk_id, embedding, metadata))
        
        # Upsert vectors to Pinecone if we have any
        if vectors:
            self.index.upsert(vectors)
            return True
        return False

    def query(self, query_embedding, top_k=5):
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )
        return results["matches"] 