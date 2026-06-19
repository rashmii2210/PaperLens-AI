// src/components/Dropzone.js
import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

function Dropzone({ onFileSelect, disabled }) {
  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles[0]) onFileSelect(acceptedFiles[0]);
  }, [onFileSelect]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    disabled,
  });

  return (
    <div
      {...getRootProps()}
      style={{
        border: '2px dashed #6c63ff',
        borderRadius: '12px',
        padding: '40px',
        textAlign: 'center',
        cursor: disabled ? 'not-allowed' : 'pointer',
        background: isDragActive ? '#f0eeff' : '#fafafa',
        transition: 'all 0.2s',
      }}
    >
      <input {...getInputProps()} />
      <div style={{ fontSize: '48px' }}>📄</div>
      {isDragActive ? (
        <p style={{ color: '#6c63ff', fontWeight: 'bold' }}>Drop karo!</p>
      ) : (
        <>
          <p style={{ color: '#333', fontWeight: 'bold' }}>
            Drag and drop your PDF here
          </p>
          <p style={{ color: '#888', fontSize: '14px' }}>
            or click to browse local files
          </p>
        </>
      )}
    </div>
  );
}

export default Dropzone;