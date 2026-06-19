// src/components/VideoPlayer.js

function VideoPlayer({ videoUrl, title }) {
  return (
    <div style={{ marginTop: '24px' }}>
      <h3 style={{ color: '#333', marginBottom: '12px' }}>
        Video Ready: {title}
      </h3>
      <video
        controls
        width="100%"
        style={{ borderRadius: '12px', background: '#000' }}
        src={videoUrl}
      >
        Your browser does not support video.
      </video>
      <a
        href={videoUrl}
        download="research_video.mp4"
        style={{
          display: 'inline-block',
          marginTop: '16px',
          padding: '12px 24px',
          background: '#6c63ff',
          color: 'white',
          borderRadius: '8px',
          textDecoration: 'none',
          fontWeight: 'bold',
        }}
      >
        Download Video
      </a>
    </div>
  );
}

export default VideoPlayer;