from storage_service import StorageService
import os

def test_gcs():
    # Create a test file
    with open("test_file.txt", "w") as f:
        f.write("This is a test file for Google Cloud Storage")
    
    # Initialize storage service
    storage = StorageService()
    
    # Upload the file
    gcs_path = storage.upload_file("test_file.txt", "test_file.txt")
    print(f"Uploaded file to: {gcs_path}")
    
    # List all files
    files = storage.list_files()
    print(f"Files in bucket: {files}")
    
    # Clean up test file
    os.remove("test_file.txt")

if __name__ == "__main__":
    test_gcs()