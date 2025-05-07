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
                    IMPORTANT: Tag this document STRICTLY based on ONLY these four categories:
                    - Action: How the content is used (MUST be one of: 'Lecture', 'Assignment', 'Reading', 'Exercise', 'Quiz', 'Lab', 'Project', 'Discussion', 'Demonstration')
                    - Relationships: How content connects (MUST be one of: 'Student-Led', 'Group Work', 'Prerequisite', 'Follow-up', 'Reference', 'Supplemental', 'Core', 'Optional', 'Collaborative')
                    - Discipline: Subject matter area (MUST be one of: 'Mathematics', 'Biology', 'Chemistry', 'Physics', 'Computer Science', 'Literature', 'History', 'Psychology', 'Economics', 'Art', 'Music')
                    - Purpose: Educational goal (MUST be one of: 'Conceptual Understanding', 'Skill Building', 'Assessment', 'Critical Thinking', 'Application', 'Review', 'Introduction', 'Analysis', 'Synthesis')
                    \nYou MUST use ONLY the exact tags listed above. Do not create new tags.\nReturn JSON with these categories as keys, each with 1-3 appropriate tags from the provided options."""},
                    {"role": "user", "content": f"Document to tag: {content[:5000]}... (truncated)"}
                ],
                response_format={"type": "json_object"}
            )
            tags = self._parse_tags(tag_response.choices[0].message.content)
            return chunks, tags
    
    def search_content(self, query, all_processed_docs):
        """Send all chunked content as context to GPT for answering the query."""
        # Flatten all chunks into a single context string
        context_chunks = []
        for doc in all_processed_docs:
            for chunk in doc.get("chunks", []):
                context_chunks.append(
                    f"Source: {doc.get('filename', '')}\nTags: {json.dumps(doc.get('tags', {}))}\nContent: {chunk.get('text', '')}\n"
                )
        context = "\n---\n".join(context_chunks)

        # Compose the prompt
        prompt = (
            f"You are an educational content assistant. "
            f"Use the following content to answer the user's question. "
            f"Reference specific sources if possible.\n\n"
            f"User question: {query}\n\n"
            f"Available content:\n{context}"
        )

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an educational content assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        return {
            "query": query,
            "reply": response.choices[0].message.content
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