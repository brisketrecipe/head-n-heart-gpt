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

const ProgressBar = styled.div`
  width: 100%;
  background: #eee;
  border-radius: 6px;
  margin-top: 1rem;
  height: 16px;
  overflow: hidden;
`;
const ProgressFill = styled.div`
  height: 100%;
  background: #2c3e50;
  width: ${props => props.percent}%;
  transition: width 0.2s;
`;

function DocumentUpload() {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState(null);
  const [uploadProgress, setUploadProgress] = useState({});
  const [overallProgress, setOverallProgress] = useState(0);

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
    setUploadProgress({});
    setOverallProgress(0);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();
        formData.append('file', file);

        await axios.post('/api/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(prev => ({
              ...prev,
              [file.name]: percentCompleted
            }));
            // Calculate overall progress
            const totalProgress = files.reduce((acc, f, idx) => {
              return acc + (uploadProgress[f.name] || (idx < i ? 100 : 0));
            }, 0);
            setOverallProgress(Math.round(totalProgress / files.length));
          }
        });
      }
      setStatus({ success: true, message: 'Files uploaded successfully!' });
      setFiles([]);
      setUploadProgress({});
      setOverallProgress(100);
    } catch (error) {
      setStatus({ success: false, message: 'Error uploading files. Please try again.' });
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
                <span>
                  {uploadProgress[file.name] ? `${uploadProgress[file.name]}%` : ''}
                </span>
                <button onClick={() => removeFile(index)}>Remove</button>
              </FileItem>
            ))}
          </FileList>
          <ProgressBar>
            <ProgressFill percent={overallProgress} />
          </ProgressBar>
          <UploadButton
            onClick={uploadFiles}
            disabled={uploading}
          >
            {uploading ? `Uploading... (${overallProgress}%)` : 'Upload Files'}
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