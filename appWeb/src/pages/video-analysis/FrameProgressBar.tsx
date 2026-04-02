// FrameProgressBar — renders only when a progress ratio is calculable.
// Follows Zeigarnik effect: visible progress motivates completion.

interface FrameProgressBarProps {
  /** Value 0..1. Pass null/undefined to hide the bar entirely. */
  progress: number | null;
  frameIndex: number;
  totalFrames: number | null;
}

export function FrameProgressBar({ progress, frameIndex, totalFrames }: FrameProgressBarProps) {
  if (progress == null) return null;

  return (
    <div style={{ margin: '0.75rem 0' }}>
      <div
        style={{
          position: 'relative',
          height: 6,
          background: 'var(--bm-border)',
          borderRadius: 3,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${Math.round(progress * 100)}%`,
            background: 'linear-gradient(90deg, var(--bm-accent), #2ee6b6)',
            transition: 'width 0.08s linear',
            borderRadius: 3,
          }}
        />
      </div>
      <span
        style={{
          display: 'block',
          marginTop: '0.3rem',
          fontFamily: 'var(--bm-font-mono)',
          fontSize: '0.6875rem',
          color: 'var(--bm-text-secondary)',
        }}
      >
        Frame {frameIndex + 1}
        {totalFrames != null ? ` / ${totalFrames}` : ''}
        {' '}·{' '}
        {Math.round(progress * 100)}%
      </span>
    </div>
  );
}
