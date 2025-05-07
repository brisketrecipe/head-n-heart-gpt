# from google.cloud import storage
# import os
# from datetime import datetime

# class StorageService:
#     def __init__(self, bucket_name):
#         self.client = storage.Client()
#         self.bucket = self.client.bucket(bucket_name)
        
#     def upload_file(self, file_content, filename):
#         """Upload a file to Google Cloud Storage"""
#         # Generate a unique path for the file
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#         path = f"uploads/{timestamp}_{filename}"
        
#         # Create a new blob and upload the file
#         blob = self.bucket.blob(path)
#         blob.upload_from_string(file_content)
        
#         return path
        
#     def get_file_url(self, path, expiration=3600):
#         """Generate a signed URL for file access"""
#         blob = self.bucket.blob(path)
#         return blob.generate_signed_url(
#             version="v4",
#             expiration=expiration,
#             method="GET"
#         )
        
#     def delete_file(self, path):
#         """Delete a file from storage"""
#         blob = self.bucket.blob(path)
#         blob.delete()
        
#     def list_files(self, prefix="uploads/"):
#         """List all files in the bucket with the given prefix"""
#         blobs = self.bucket.list_blobs(prefix=prefix)
#         return [blob.name for blob in blobs] 

from google.cloud import storage
import os
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