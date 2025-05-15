import os
import tempfile

# Railway secure service account injection
if os.getenv("RAILWAY") == "true":
    google_creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if google_creds_json:
        fd, temp_path = tempfile.mkstemp()
        with os.fdopen(fd, 'w') as tmp:
            tmp.write(google_creds_json)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_path

from google.cloud import storage
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class StorageService:
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name
        self.client = storage.Client()
        self.bucket = self.client.get_bucket(bucket_name)
    
    def upload_file(self, content, filename):
        """Upload original document"""
        blob = self.bucket.blob(f"documents/{filename}")
        blob.upload_from_string(content)
        return f"gs://{self.bucket_name}/documents/{filename}"
    
    def store_processed_content(self, filename, processed_data):
        """Store processed chunks and tags as JSON"""
        json_blob = self.bucket.blob(f"processed/{filename}.json")
        json_blob.upload_from_string(
            json.dumps(processed_data, indent=2),
            content_type="application/json"
        )
        return f"gs://{self.bucket_name}/processed/{filename}.json"
    
    def list_documents(self):
        """List all original documents"""
        blobs = self.client.list_blobs(self.bucket_name, prefix="documents/")
        return [blob.name.replace("documents/", "") for blob in blobs]
    
    def list_processed(self):
        """List all processed documents"""
        blobs = self.client.list_blobs(self.bucket_name, prefix="processed/")
        return [blob.name.replace("processed/", "").replace(".json", "") for blob in blobs]
    
    def get_document(self, filename):
        """Get original document"""
        blob = self.bucket.blob(f"documents/{filename}")
        return blob.download_as_bytes()
    
    def get_processed(self, filename):
        """Get processed chunks and tags"""
        blob = self.bucket.blob(f"processed/{filename}.json")
        content = blob.download_as_string()
        return json.loads(content)