import React, { useState } from 'react';
import styled from '@emotion/styled';
import axios from 'axios';

const UploadContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
`;

const UploadArea = styled.div`
  border: 2px dashed #ccc;
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    border-color: #2c3e50;
    background-color: #f8f9fa;
  }
`;

const FileInput = styled.input`
  display: none;
`;

const UploadText = styled.p`
  color: #666;
  margin-bottom: 1rem;
`;

const FileList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;
`;

const FileItem = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 6px;
`;

const FileName = styled.span`
  font-weight: 500;
`;

const UploadButton = styled.button`
  padding: 0.75rem 1.5rem;
  background-color: #2c3e50;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s ease;

  &:hover {
    background-color: #34495e;
  }

  &:disabled {
    background-color: #ccc;
    cursor: not-allowed;
  }
`;

const StatusMessage = styled.div`
  padding: 1rem;
  border-radius: 6px;
  margin-top: 1rem;
  background-color: ${props => props.success ? '#d4edda' : '#f8d7da'};
  color: ${props => props.success ? '#155724' : '#721c24'};
`;

function DocumentUpload() {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState(null);

  const handleFileSelect = (event) => {
    const selectedFiles = Array.from(event.target.files);
    setFiles(prev => [...prev, ...selectedFiles]);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    const droppedFiles = Array.from(event.dataTransfer.files);
    setFiles(prev => [...prev, ...droppedFiles]);
  };

  const handleDragOver = (event) => {
    event.preventDefault();
  };

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const uploadFiles = async () => {
    if (files.length === 0) return;

    setUploading(true);
    setStatus(null);

    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);

        await axios.post('/api/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
      }

      setStatus({
        success: true,
        message: 'Files uploaded successfully!',
      });
      setFiles([]);
    } catch (error) {
      setStatus({
        success: false,
        message: 'Error uploading files. Please try again.',
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <UploadContainer>
      <UploadArea
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onClick={() => document.getElementById('fileInput').click()}
      >
        <FileInput
          id="fileInput"
          type="file"
          multiple
          onChange={handleFileSelect}
        />
        <UploadText>
          Drag and drop files here or click to select files
        </UploadText>
        <p>Supported formats: PDF, DOCX, TXT, Images</p>
      </UploadArea>

      {files.length > 0 && (
        <>
          <FileList>
            {files.map((file, index) => (
              <FileItem key={index}>
                <FileName>{file.name}</FileName>
                <button onClick={() => removeFile(index)}>Remove</button>
              </FileItem>
            ))}
          </FileList>

          <UploadButton
            onClick={uploadFiles}
            disabled={uploading}
          >
            {uploading ? 'Uploading...' : 'Upload Files'}
          </UploadButton>
        </>
      )}

      {status && (
        <StatusMessage success={status.success}>
          {status.message}
        </StatusMessage>
      )}
    </UploadContainer>
  );
}

export default DocumentUpload; 