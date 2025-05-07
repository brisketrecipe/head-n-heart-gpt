import os
import PyPDF2
import docx
import pytesseract
from PIL import Image
import io

class DocumentProcessor:
    def extract_content(self, file_path, file_content=None):
        """Extract text from various file types, or return image bytes for images"""
        if file_content:
            file_content = io.BytesIO(file_content)
        file_extension = file_path.split('.')[-1].lower()
        if file_extension == 'pdf':
            return self._extract_from_pdf(file_content or file_path), 'text'
        elif file_extension in ['doc', 'docx']:
            return self._extract_from_docx(file_content or file_path), 'text'
        elif file_extension in ['jpg', 'jpeg', 'png']:
            # Return image bytes for further processing
            if file_content:
                file_content.seek(0)
                return file_content.read(), 'image'
            else:
                with open(file_path, 'rb') as f:
                    return f.read(), 'image'
        elif file_extension == 'txt':
            return self._extract_from_txt(file_content or file_path), 'text'
        else:
            return f"Unsupported file type: {file_extension}", 'unsupported'
    
    def _extract_from_pdf(self, source):
        """Extract text from PDF files"""
        text = ""
        with open(source, 'rb') if isinstance(source, str) else source as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text
    
    def _extract_from_docx(self, source):
        """Extract text from Word documents"""
        doc = docx.Document(source)
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])
    
    def _extract_from_image(self, source):
        # Deprecated: no longer used, replaced by GPT-4o
        return ""
        
    def _extract_from_txt(self, source):
        """Read plain text files"""
        if isinstance(source, str):
            with open(source, 'r') as file:
                return file.read()
        else:
            return source.read().decode('utf-8')
    
    def chunk_document(self, text, chunk_size=500, overlap=50):
        """Split document into chunks with overlap"""
        # First try to split by paragraphs
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # Skip empty paragraphs
            if not paragraph.strip():
                continue
                
            # If adding this paragraph exceeds chunk size, save current chunk
            if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # Keep some overlap for context
                current_chunk = current_chunk[-overlap:] if overlap > 0 else ""
            
            current_chunk += paragraph + "\n\n"
        
        # Add the last chunk if it has content
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks 