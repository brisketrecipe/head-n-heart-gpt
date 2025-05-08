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

    def upsert_chunks(self, filename, chunks, tags):
        vectors = []
        tags_str = json.dumps(tags)  # Stringify tags for Pinecone metadata
        for i, chunk in enumerate(chunks):
            vectors.append((f"{filename}-chunk-{i}", chunk["embedding"], {
                "filename": filename,
                "tags": tags_str,  # Store as string
                "chunkText": chunk["text"],
                "chunkIndex": i
            }))
        self.index.upsert(vectors)

    def query(self, query_embedding, top_k=5):
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )
        return results["matches"] 