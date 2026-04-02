// SnackBar — fixed-position toast that auto-dismisses.
// Rendered at the VideoAnalysisPage root so it overlays everything.

interface SnackBarProps {
  message: string | null;
}

export function SnackBar({ message }: SnackBarProps) {
  if (!message) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        position: 'fixed',
        bottom: 24,
        left: '50%',
        transform: 'translateX(-50%)',
        background: 'var(--bm-accent-muted)',
        color: 'var(--bm-accent)',
        border: '1px solid rgba(0,230,118,0.2)',
        padding: '0.75rem 1.25rem',
        borderRadius: 'var(--bm-radius-sm)',
        zIndex: 900,
        fontFamily: 'var(--bm-font-body)',
        fontSize: '0.875rem',
        fontWeight: 500,
        whiteSpace: 'nowrap',
        pointerEvents: 'none',
      }}
    >
      {message}
    </div>
  );
}
