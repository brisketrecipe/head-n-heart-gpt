import pinecone
from openai import OpenAI
import logging

class VectorStore:
    def __init__(self, pinecone_api_key, openai_api_key, index_name="educational-content"):
        try:
            # Initialize Pinecone with the new client
            self.pc = pinecone.Pinecone(
                api_key=pinecone_api_key,
                environment="us-east-1"
            )
            
            # Create index if it doesn't exist
            if index_name not in self.pc.list_indexes():
                self.pc.create_index(
                    name=index_name,
                    spec={
                        "serverless": {
                            "cloud": "aws",
                            "region": "us-east-1"
                        },
                        "dimension": 1536,  # OpenAI embeddings dimension
                        "metric": "cosine"
                    }
                )
                
            self.index = self.pc.Index(index_name)
            self.openai_client = OpenAI(api_key=openai_api_key)
            logging.info(f"Successfully initialized Pinecone index: {index_name}")
        except Exception as e:
            logging.error(f"Error initializing Pinecone: {str(e)}")
            raise
        
    def store_chunk(self, chunk_text, metadata):
        """Generate embedding and store in Pinecone"""
        try:
            embedding = self._generate_embedding(chunk_text)
            
            if embedding:
                self.index.upsert(
                    vectors=[(metadata["id"], embedding, metadata)]
                )
                logging.info(f"Successfully stored chunk: {metadata['id']}")
                return True
            return False
        except Exception as e:
            logging.error(f"Error storing chunk: {str(e)}")
            return False
            
    def search(self, query, filters=None, top_k=20):
        """Search for similar chunks"""
        try:
            query_embedding = self._generate_embedding(query)
            
            if not query_embedding:
                return []
                
            results = self.index.query(
                vector=query_embedding,
                filter=filters,
                top_k=top_k,
                include_metadata=True
            )
            
            logging.info(f"Found {len(results.matches)} matches for query")
            return results.matches
        except Exception as e:
            logging.error(f"Error searching: {str(e)}")
            return []
        
    def _generate_embedding(self, text):
        """Generate embeddings using OpenAI API"""
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model="text-embedding-3-large"
            )
            return response.data[0].embedding
        except Exception as e:
            logging.error(f"Error generating embedding: {str(e)}")
            return None 