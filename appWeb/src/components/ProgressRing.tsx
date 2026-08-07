import './ui.css';

/** Arco de progreso 0–1 (objetivo de repeticiones). */
export function ProgressRing({ progress, label }: { progress: number; label?: string }) {
  const p = Math.min(1, Math.max(0, progress));
  const r = 14;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - p);
  return (
    <div className="progress-ring-wrap">
      <svg className="progress-ring" viewBox="0 0 36 36" aria-hidden>
        <circle className="progress-ring__bg" cx="18" cy="18" r={r} />
        <circle
          className="progress-ring__fg"
          cx="18"
          cy="18"
          r={r}
          strokeDasharray={c}
          strokeDashoffset={offset}
        />
      </svg>
      {label ? <span className="bm-caption">{label}</span> : null}
    </div>
  );
}
