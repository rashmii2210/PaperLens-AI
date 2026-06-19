// src\App.js
import { useState } from 'react';
import Dropzone from './components/Dropzone';
import ProgressBar from './components/ProgressBar';
import VideoPlayer from './components/VideoPlayer';

const STEPS = [
  { label: 'PDF Upload' },
  { label: 'Script Generation (AI)' },
  { label: 'Audio Generation' },
  { label: 'Video Assembly' },
];

function App() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('idle');
  const [currentStep, setCurrentStep] = useState(-1);
  const [videoUrl, setVideoUrl] = useState(null);
  const [paperTitle, setPaperTitle] = useState('');
  const [error, setError] = useState(null);

  const handleFileSelect = (selectedFile) => {
    setFile(selectedFile);
    setStatus('idle');
    setVideoUrl(null);
    setError(null);
    setCurrentStep(-1);
  };

  const handleGenerate = async () => {
    if (!file) return;

    setStatus('processing');
    setError(null);
    setCurrentStep(0);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const uploadRes = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });
      const uploadData = await uploadRes.json();
      const taskId = uploadData.task_id;

      const poll = setInterval(async () => {
        const statusRes = await fetch(`http://localhost:8000/status/${taskId}`);
        const statusData = await statusRes.json();

        setCurrentStep(statusData.step);

        if (statusData.state === 'SUCCESS') {
          clearInterval(poll);
          setVideoUrl(statusData.video_url);
          setPaperTitle(statusData.title);
          setStatus('done');
        } else if (statusData.state === 'FAILURE') {
          clearInterval(poll);
          setError(statusData.message);
          setStatus('idle');
        }
      }, 3000);

    } catch (err) {
      setError('Failed to communicate document transmission to server api');
      setStatus('idle');
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%)',
      display: 'flex',
      alignItems: 'flex-start',
      justifyContent: 'center',
      padding: '40px 16px',
    }}>
      <div style={{
        background: 'white',
        borderRadius: '20px',
        padding: '40px',
        width: '100%',
        maxWidth: '640px',
        boxShadow: '0 8px 32px rgba(108,99,255,0.12)',
      }}>

        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <h1 style={{ color: '#6c63ff', fontSize: '28px', margin: 0 }}>
            PaperLens AI
          </h1>
          <p style={{ color: '#888', marginTop: '8px' }}>
           Transform comprehensive documents into narrated overview media assets.
          </p>
        </div>

        <Dropzone
          onFileSelect={handleFileSelect}
          disabled={status === 'processing'}
        />

        {file && status === 'idle' && (
          <div style={{
            marginTop: '16px',
            padding: '12px 16px',
            background: '#f0eeff',
            borderRadius: '8px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span style={{ color: '#6c63ff', fontWeight: 'bold' }}>
              {file.name}
            </span>
            <span style={{ color: '#888', fontSize: '13px' }}>
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </span>
          </div>
        )}

        {file && status === 'idle' && (
          <button
            onClick={handleGenerate}
            style={{
              width: '100%',
              marginTop: '20px',
              padding: '14px',
              background: '#6c63ff',
              color: 'white',
              border: 'none',
              borderRadius: '10px',
              fontSize: '16px',
              fontWeight: 'bold',
              cursor: 'pointer',
            }}
          >
            Generate Video
          </button>
        )}

        {status === 'processing' && (
          <div style={{ marginTop: '24px' }}>
            <ProgressBar steps={STEPS} currentStep={currentStep} />
          </div>
        )}

        {error && (
          <div style={{
            marginTop: '16px',
            padding: '12px',
            background: '#fff0f0',
            border: '1px solid #ffcccc',
            borderRadius: '8px',
            color: '#cc0000',
          }}>
            {error}
          </div>
        )}

        {status === 'done' && videoUrl && (
          <VideoPlayer videoUrl={videoUrl} title={paperTitle} />
        )}

      </div>
    </div>
  );
}

export default App;