import os
import json
import base64
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class OpenAIService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def process_document(self, content, filename, filetype='text'):
        """Process document - both chunking and tagging. If image, use GPT-4o vision."""
        if filetype == 'image':
            # Encode image to base64
            base64_image = base64.b64encode(content).decode('utf-8')
            # Prepare the API request for GPT-4o
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Chunk and tag this educational image. Return a JSON object with: chunks (array of objects with text, summary, context), and tags (object with Action, Relationships, Discipline, Purpose)."},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }
            ]
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=1000
            )
            # Try to extract JSON from the response
            content = response.choices[0].message.content
            try:
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    result = json.loads(json_str)
                    chunks = result.get('chunks', [])
                    tags = result.get('tags', {})
                    return chunks, tags
                else:
                    return [], {}
            except Exception:
                return [], {}
        else:
            # Text-based processing (existing logic)
            chunk_response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": """You are an expert document processor. 
                    Your task is to break this document into meaningful chunks that preserve 
                    context and meaning. Each chunk should be about 300-500 words. For each 
                    chunk, provide a brief description of its content.
                    Return a JSON object with an array of chunks, where each chunk has:
                    - text: the actual content
                    - summary: a brief description of what the chunk contains
                    - context: any important context needed to understand the chunk"""},
                    {"role": "user", "content": f"Here's the document to process: {content[:10000]}... (truncated)"}
                ],
                response_format={"type": "json_object"}
            )
            chunks = self._parse_chunks(chunk_response.choices[0].message.content)
            tag_response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": """You are a document tagging expert. 
                    Tag this document based on these categories:
                    - Action: How the content is used (e.g., \"Lecture\", \"Assignment\", \"Reading\")
                    - Relationships: How content connects with people/other content
                    - Discipline: Subject matter area
                    - Purpose: Educational goal
                    Return JSON with these categories as keys, each with 1-3 appropriate tags."""},
                    {"role": "user", "content": f"Document to tag: {content[:5000]}... (truncated)"}
                ],
                response_format={"type": "json_object"}
            )
            tags = self._parse_tags(tag_response.choices[0].message.content)
            return chunks, tags
    
    def search_content(self, query, all_processed_docs):
        """Search across all processed content using GPT"""
        # Prepare a summary of available content for GPT
        content_summary = self._prepare_content_summary(all_processed_docs)
        
        # Ask GPT to identify which documents/chunks are most relevant
        search_response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": """You are a document retrieval system.
                Your task is to identify which documents and chunks are most relevant to 
                the user's query based on the summaries provided. Return the IDs of the 
                top 5-10 most relevant chunks."""},
                {"role": "user", "content": f"Query: {query}\n\nAvailable Content: {content_summary}"}
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse relevant chunks
        relevant_chunks = self._parse_search_results(search_response.choices[0].message.content)
        
        # Fetch the actual content of those chunks
        retrieved_chunks = self._fetch_chunks(relevant_chunks, all_processed_docs)
        
        # Generate a response based on the retrieved chunks
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": """You are an educational content assistant.
                Based on the retrieved content chunks, provide a helpful response to the 
                user's query about educational materials."""},
                {"role": "user", "content": f"Query: {query}\n\nRetrieved content: {retrieved_chunks}"}
            ]
        )
        
        return {
            "query": query,
            "suggestions": response.choices[0].message.content,
            "relevant_chunks": retrieved_chunks
        }
    
    def _parse_chunks(self, response_text):
        """Parse GPT's chunking response"""
        try:
            return json.loads(response_text).get("chunks", [])
        except:
            return []
    
    def _parse_tags(self, response_text):
        """Parse GPT's tagging response"""
        try:
            return json.loads(response_text)
        except:
            return {}
    
    def _prepare_content_summary(self, all_processed_docs):
        """Prepare a summary of all processed documents for GPT"""
        summary = []
        for doc in all_processed_docs:
            for chunk in doc.get("chunks", []):
                summary.append({
                    "id": f"{doc['filename']}_{chunk.get('id', '')}",
                    "summary": chunk.get("summary", ""),
                    "context": chunk.get("context", "")
                })
        return json.dumps(summary)
    
    def _parse_search_results(self, response_text):
        """Parse GPT's search results"""
        try:
            return json.loads(response_text).get("relevant_chunks", [])
        except:
            return []
    
    def _fetch_chunks(self, chunk_ids, all_processed_docs):
        """Fetch the actual content of the relevant chunks"""
        chunks = []
        for doc in all_processed_docs:
            for chunk in doc.get("chunks", []):
                chunk_id = f"{doc['filename']}_{chunk.get('id', '')}"
                if chunk_id in chunk_ids:
                    chunks.append({
                        "id": chunk_id,
                        "source": doc["filename"],
                        "text": chunk.get("text", ""),
                        "summary": chunk.get("summary", ""),
                        "context": chunk.get("context", ""),
                        "tags": doc.get("tags", {})
                    })
        return chunks 