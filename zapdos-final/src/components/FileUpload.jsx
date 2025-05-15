// src/components/FileUpload.jsx
import React from 'react';
import { useDropzone } from 'react-dropzone';
import { FaFileAlt, FaUpload } from 'react-icons/fa';

const FileUpload = ({ onFileUpload, isLoading }) => {
  const acceptedFileTypes = {
    'image/jpeg': ['.jpeg', '.jpg'],
    'image/png': ['.png'],
    'image/gif': ['.gif'],
    'image/bmp': ['.bmp'],
    'image/webp': ['.webp'],
    'application/pdf': ['.pdf'],
    'application/msword': ['.doc'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    'application/vnd.ms-powerpoint': ['.ppt'],
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
    'text/plain': ['.txt']
  };

  const onDrop = React.useCallback(acceptedFiles => {
    if (acceptedFiles.length > 0 && !isLoading) {
      onFileUpload(acceptedFiles[0]); 
    }
  }, [onFileUpload, isLoading]);

  const { getRootProps, getInputProps, isDragActive, acceptedFiles: droppedAcceptedFiles } = useDropzone({
    onDrop,
    multiple: false,
    accept: acceptedFileTypes,
    disabled: isLoading,
  });

  const displayedFileName = droppedAcceptedFiles.length > 0 ? droppedAcceptedFiles[0].name : null;

  return (
    <div 
      {...getRootProps()} 
      className={`file-upload-container neumorphism-card ${isDragActive ? 'drag-over' : ''} ${isLoading ? 'loading' : ''}`}
      style={{
        minHeight: '250px', 
        padding: '30px',
        borderStyle: isLoading ? 'solid' : 'dashed', 
        borderColor: isDragActive ? '#88a2c4' : (isLoading ? ' #bdc7d3' : ' #bdc7d3'),
        cursor: isLoading ? 'default' : 'pointer'
      }}
    >
      <input {...getInputProps()} />
      <>
        {displayedFileName && !isLoading ? (
          <>
            <FaFileAlt className="upload-icon" style={{color: '#5c67f2', fontSize: '3.5rem'}}/>
            <p style={{fontWeight: '600', marginTop: '15px'}}>{displayedFileName}</p>
            <p style={{fontSize: '0.9rem', color: '#777'}}>File ready. Drop another or click to change.</p>
          </>
        ) : (
          <>
            <FaUpload className="upload-icon" style={{fontSize: '3.5rem'}}/>
            {isDragActive ? (
              <p>Drop the file here to select...</p>
            ) : (
              <p>Drag & drop a file, or click to select</p>
            )}
            <p style={{fontSize: '0.85rem', color: '#777', marginTop: '5px'}}>
              (PDF, JPG, PNG, GIF, etc.)
            </p>
          </>
        )}
      </>
    </div>
  );
};

export default FileUpload;