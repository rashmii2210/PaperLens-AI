//src/components/ProgressBar.js

function ProgressBar({ steps, currentStep }) {
  return (
    <div style={{ margin: '24px 0' }}>
      {steps.map((step, i) => {
        const isDone = i < currentStep;
        const isActive = i === currentStep;

        return (
          <div
            key={i}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              marginBottom: '12px',
              opacity: i > currentStep ? 0.3 : 1,
              transition: 'opacity 0.3s',
            }}
          >
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                background: isDone ? '#6c63ff' : isActive ? '#a89cff' : '#ddd',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                fontWeight: 'bold',
                fontSize: '14px',
                flexShrink: 0,
              }}
            >
              {isDone ? '✓' : i + 1}
            </div>
            <div>
              <div style={{ fontWeight: isActive ? 'bold' : 'normal', color: '#333' }}>
                {step.label}
              </div>
              {isActive && (
                <div style={{ fontSize: '13px', color: '#6c63ff' }}>
                  Processing...
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default ProgressBar;