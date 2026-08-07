export function StatusPill({ status }: { status: string }) {
  const color =
    status === 'completed'
      ? 'var(--bm-accent)'
      : status === 'running'
        ? 'var(--bm-angle-warn)'
        : status === 'failed'
          ? 'var(--bm-angle-bad)'
          : 'var(--bm-text-secondary)';
  return (
    <span className="bm-caption" style={{ color, fontWeight: 600 }}>
      {status}
    </span>
  );
}
