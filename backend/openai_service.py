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
        """Process document - treat each page/document as a single chunk with up to 5 ranked tags"""
        # Define the valid competencies for strict validation
        valid_competencies = [
            "Results", "Execution", "Fearless Presenter", "Seize Opportunities",
            "Connection", "Leadership", "Collaboration", "Awareness",
            "Planning", "Constructive Thinking", "Organize", "Control",
            "Authenticity", "CEO Perspective", "Vision", "Growth Mindset"
        ]
        
        if filetype == 'image':
            # Encode image to base64
            base64_image = base64.b64encode(content).decode('utf-8')
            # Prepare the API request for GPT-4o with updated prompt for strict tagging
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": """Analyze this educational image and classify it. 

Return a JSON object with:
1. "text": All visible text from the image
2. "summary": A brief description of the image content (2-3 sentences)
3. "tags": An array of EXACTLY the most relevant competencies from this list (maximum 5, ranked by relevance):
   - Results
   - Execution
   - Fearless Presenter
   - Seize Opportunities
   - Connection
   - Leadership
   - Collaboration
   - Awareness
   - Planning
   - Constructive Thinking
   - Organize
   - Control
   - Authenticity
   - CEO Perspective
   - Vision
   - Growth Mindset

IMPORTANT: The tags must be exactly as written above - no variations. List them in order of relevance with the most relevant first.
Respond ONLY with a valid JSON object."""},
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
                    
                    # Create a single chunk with tags
                    chunk = {
                        "text": result.get("text", ""),
                        "summary": result.get("summary", ""),
                        "context": "",
                        "chunk_id": f"{filename}_image",
                        "tags": self._validate_tags(result.get("tags", []), valid_competencies)
                    }
                    
                    return [chunk], {}  # Return as a list with a single chunk
                else:
                    return [], {}
            except Exception as e:
                print(f"Error processing image: {str(e)}")
                return [], {}
                
        elif isinstance(content, list):  # PDF: list of page texts
            all_processed_chunks = []
            
            for i, page_text in enumerate(content):
                if not page_text.strip():
                    continue
                
                # Treat each page as a single chunk - no sub-chunking
                # Create a summary for the page
                summary_response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are an expert at summarizing educational content."},
                        {"role": "user", "content": f"Provide a brief 2-3 sentence summary of this page from an educational document:\n\n{page_text[:5000]}... (truncated if longer)"}
                    ],
                    max_tokens=200
                )
                
                page_summary = summary_response.choices[0].message.content.strip()
                
                # Tag the entire page with strict tags
                tag_response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": """You are a document tagging expert specializing in entrepreneurship education.

STRICTLY classify this educational content using the EXACT competencies from this list:

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

INSTRUCTIONS:
1. Return a JSON array with a MAXIMUM of 5 competencies that this content addresses
2. Only use the EXACT competency names listed above - no variations whatsoever
3. List them in order of relevance (most relevant first)
4. Only include competencies that are substantially addressed in the content
5. If fewer than 5 competencies are relevant, include fewer - quality over quantity

Example correct response:
["Vision", "Leadership", "Planning", "Authenticity"]

Respond ONLY with a valid JSON array of competencies."""},
                        {"role": "user", "content": f"Document content to tag: {page_text[:7000]}... (truncated if longer)"}
                    ]
                )
                
                page_tags = self._parse_tags(tag_response.choices[0].message.content)
                page_tags = self._validate_tags(page_tags, valid_competencies)
                
                # Create a single chunk for this page
                chunk = {
                    "text": page_text,
                    "summary": page_summary,
                    "context": f"Page {i+1} of document",
                    "chunk_id": f"{filename}_page{i+1}",
                    "tags": page_tags
                }
                
                all_processed_chunks.append(chunk)
                    
            return all_processed_chunks, {}  # Return empty dict for backwards compatibility
            
        else:
            # Text-based processing - keep as whole document or split by natural sections if very large
            if len(content) > 10000:
                # If document is large, process in sections
                sections = self._split_into_sections(content)
                processed_chunks = []
                
                for i, section in enumerate(sections):
                    # Create summary for section
                    summary_response = self.client.chat.completions.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": "You are an expert at summarizing educational content."},
                            {"role": "user", "content": f"Provide a brief 2-3 sentence summary of this section from an educational document:\n\n{section[:5000]}... (truncated if longer)"}
                        ],
                        max_tokens=200
                    )
                    
                    section_summary = summary_response.choices[0].message.content.strip()
                    
                    # Tag the section with strict tags
                    tag_response = self.client.chat.completions.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": """You are a document tagging expert specializing in entrepreneurship education.

STRICTLY classify this educational content using the EXACT competencies from this list:

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

INSTRUCTIONS:
1. Return a JSON array with a MAXIMUM of 5 competencies that this content addresses
2. Only use the EXACT competency names listed above - no variations whatsoever
3. List them in order of relevance (most relevant first)
4. Only include competencies that are substantially addressed in the content
5. If fewer than 5 competencies are relevant, include fewer - quality over quantity

Example correct response:
["Vision", "Leadership", "Planning", "Authenticity"]

Respond ONLY with a valid JSON array of competencies."""},
                            {"role": "user", "content": f"Document content to tag: {section[:7000]}... (truncated if longer)"}
                        ]
                    )
                    
                    section_tags = self._parse_tags(tag_response.choices[0].message.content)
                    section_tags = self._validate_tags(section_tags, valid_competencies)
                    
                    # Create a chunk for this section
                    chunk = {
                        "text": section,
                        "summary": section_summary,
                        "context": f"Section {i+1} of document",
                        "chunk_id": f"{filename}_section{i+1}",
                        "tags": section_tags
                    }
                    
                    processed_chunks.append(chunk)
            else:
                # For smaller documents, process as a single chunk
                # Create summary
                summary_response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are an expert at summarizing educational content."},
                        {"role": "user", "content": f"Provide a brief 2-3 sentence summary of this educational document:\n\n{content[:5000]}... (truncated if longer)"}
                    ],
                    max_tokens=200
                )
                
                summary = summary_response.choices[0].message.content.strip()
                
                # Tag the document with strict tags
                tag_response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": """You are a document tagging expert specializing in entrepreneurship education.

STRICTLY classify this educational content using the EXACT competencies from this list:

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

INSTRUCTIONS:
1. Return a JSON array with a MAXIMUM of 5 competencies that this content addresses
2. Only use the EXACT competency names listed above - no variations whatsoever
3. List them in order of relevance (most relevant first)
4. Only include competencies that are substantially addressed in the content
5. If fewer than 5 competencies are relevant, include fewer - quality over quantity

Example correct response:
["Vision", "Leadership", "Planning", "Authenticity"]

Respond ONLY with a valid JSON array of competencies."""},
                        {"role": "user", "content": f"Document content to tag: {content[:7000]}... (truncated if longer)"}
                    ]
                )
                
                document_tags = self._parse_tags(tag_response.choices[0].message.content)
                document_tags = self._validate_tags(document_tags, valid_competencies)
                
                # Create a single chunk for the entire document
                chunk = {
                    "text": content,
                    "summary": summary,
                    "context": "Complete document",
                    "chunk_id": f"{filename}_full",
                    "tags": document_tags
                }
                
                processed_chunks = [chunk]
                
            return processed_chunks, {}  # Return empty dict for backwards compatibility
    
    def _validate_tags(self, tags, valid_competencies):
        """Validate and sanitize tags to ensure they match our requirements"""
        if not isinstance(tags, list):
            return []
            
        # Filter to only include valid competencies with exact matching
        valid_tags = [tag for tag in tags if tag in valid_competencies]
        
        # Limit to 5 tags
        return valid_tags[:5]
        
    def _split_into_sections(self, content):
        """Split large documents into logical sections based on headings or natural breaks"""
        # Simple implementation - split by double newlines
        sections = []
        current_section = ""
        lines = content.split('\n')
        
        for line in lines:
            current_section += line + "\n"
            
            # If we hit a section break or accumulated enough text
            if (line.strip() == "" and current_section.count('\n') > 3) or len(current_section) > 7000:
                if current_section.strip():
                    sections.append(current_section.strip())
                current_section = ""
                
        # Add any remaining content
        if current_section.strip():
            sections.append(current_section.strip())
            
        # If we ended up with no sections, return the whole thing as one section
        if not sections:
            return [content]
            
        return sections
    
    def search_content(self, query, all_processed_docs):
        """Send all chunked content as context to GPT for answering the query."""
        # Flatten all chunks into a single context string
        context_chunks = []
        for doc in all_processed_docs:
            for chunk in doc.get("chunks", []):
                context_chunks.append(
                    f"Source: {doc.get('filename', '')}\nTags: {json.dumps(chunk.get('tags', []))}\nContent: {chunk.get('text', '')}\n"
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
            try:
                # Try to parse as direct JSON object if not in expected format
                return [json.loads(response_text)]
            except:
                return []
    
    def _parse_tags(self, response_text):
        """Parse GPT's tagging response"""
        try:
            return json.loads(response_text)
        except:
            return []
    
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