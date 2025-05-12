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
        """Process document - both chunking and tagging. If image, use GPT-4o vision. If list, process each item (PDF page) individually."""
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
        elif isinstance(content, list):  # PDF: list of page texts
            all_chunks = []
            all_tags = []
            for i, page_text in enumerate(content):
                if not page_text.strip():
                    continue
                chunk_response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": """You are an expert document processor for educational content.\nYour task is to break this document into meaningful chunks that preserve\ncontext and meaning. Each chunk should be about 300-500 words and represent a coherent concept or section. \n\nReturn a JSON object with an array of chunks, where each chunk has:\n- text: the actual content\n- summary: a brief description of what the chunk contains (2-3 sentences)\n- context: any important context needed to understand the chunk\n\nMake sure chunks maintain coherence and do not break mid-paragraph or mid-concept.\nRespond ONLY with a valid JSON object."""},
                        {"role": "user", "content": f"Here's page {i+1} of the document to process:\n{page_text}"}
                    ]
                )
                page_chunks = self._parse_chunks(chunk_response.choices[0].message.content)
                tag_response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": """You are a document tagging expert specializing in entrepreneurship education.\n\nFor each chunk of educational content, identify which of the following 16 specific behavioral competencies from the Wolff Center for Entrepreneurship (WCE) are most relevant:\n\nACTION category:\n- Results\n- Execution\n- Fearless Presenter\n- Seize Opportunities\n\nRELATIONSHIPS category:\n- Connection\n- Leadership\n- Collaboration\n- Awareness\n\nDISCIPLINE category:\n- Planning\n- Constructive Thinking\n- Organize\n- Control\n\nPURPOSE category:\n- Authenticity\n- CEO Perspective\n- Vision\n- Growth Mindset\n\nReturn a JSON object with an array of the most relevant competencies (no more than 5) that this chunk clearly addresses.\nExample: [\"Fearless Presenter\", \"Leadership\", \"Vision\"]\n\nOnly include competencies that are substantially addressed in the content.\nRespond ONLY with a valid JSON object."""},
                        {"role": "user", "content": f"Document chunk to tag: {page_text[:5000]}... (truncated)"}
                    ]
                )
                page_tags = self._parse_tags(tag_response.choices[0].message.content)
                all_chunks.extend(page_chunks)
                all_tags.append(page_tags)
            return all_chunks, all_tags
        else:
            # Text-based processing (existing logic)
            chunk_response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                   {"role": "system", "content": """You are an expert document processor for educational content.
Your task is to break this document into meaningful chunks that preserve
context and meaning. Each chunk should be about 300-500 words and represent a coherent concept or section. 

Return a JSON object with an array of chunks, where each chunk has:
- text: the actual content
- summary: a brief description of what the chunk contains (2-3 sentences)
- context: any important context needed to understand the chunk

Make sure chunks maintain coherence and do not break mid-paragraph or mid-concept.
Respond ONLY with a valid JSON object."""},
                    {"role": "user", "content": f"Here's the document to process: {content[:10000]}... (truncated)"}
                ]
            )
            chunks = self._parse_chunks(chunk_response.choices[0].message.content)
            tag_response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                      {"role": "system", "content": """You are a document tagging expert specializing in entrepreneurship education.

For each chunk of educational content, identify which of the following 16 specific behavioral competencies from the Wolff Center for Entrepreneurship (WCE) are most relevant:

ACTION category:
- Results
- Execution
- Fearless Presenter
- Seize Opportunities

RELATIONSHIPS category:
- Connection
- Leadership
- Collaboration
- Awareness

DISCIPLINE category:
- Planning
- Constructive Thinking
- Organize
- Control

PURPOSE category:
- Authenticity
- CEO Perspective
- Vision
- Growth Mindset

Return a JSON object with an array of the most relevant competencies (no more than 5) that this chunk clearly addresses.
Example: ["Fearless Presenter", "Leadership", "Vision"]

Only include competencies that are substantially addressed in the content.
Respond ONLY with a valid JSON object."""}, 
                    {"role": "user", "content": f"Document chunk to tag: {content[:5000]}... (truncated)"}
                ]
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

    def extract_text_from_image(self, image_bytes, filename=None):
        """Extract all text from an image (or image-based PDF) using GPT-4o vision."""
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract all readable text from this image. Return only the extracted text as a string. If the image is a document, preserve the reading order as best as possible."},
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
            max_tokens=2000
        )
        # Return the raw text content
        return response.choices[0].message.content.strip()

    def extract_text_from_file(self, file_bytes, filename=None):
        """Extract all readable text from a file (PDF, DOCX, TXT) using GPT-4o (text model, not vision)."""
        # Encode file as base64 to send as a string (if needed)
        base64_file = base64.b64encode(file_bytes).decode('utf-8')
        ext = filename.split('.')[-1].lower() if filename else ''
        prompt = (
            f"Extract all readable text from the following {ext.upper()} file. "
            "Return only the extracted text as a string. If the file is a document, preserve the reading order as best as possible. "
            "The file is base64-encoded below:\n\n"
            f"BASE64 FILE:\n{base64_file}"
        )
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000
        )
        return response.choices[0].message.content.strip() 