import type { FrameLogEntry } from '../lib/frameLogEntry';
import './ui.css';

const statusDot: Record<string, string> = {
  good: 'var(--bm-angle-good)',
  warn: 'var(--bm-angle-warn)',
  bad: 'var(--bm-angle-bad)',
  neutral: 'var(--bm-text-disabled)',
};

export function FrameLogPanel({ entries }: { entries: FrameLogEntry[] }) {
  if (entries.length === 0) {
    return <p className="bm-caption">El log de fotogramas aparecerá al iniciar el análisis.</p>;
  }
  const rev = [...entries].reverse();
  return (
    <div className="frame-log">
      <div
        className="frame-log__row bm-caption"
        style={{ fontWeight: 700, borderBottom: '2px solid var(--bm-border)' }}
      >
        <span className="bm-mono">#</span>
        <span>Izq.</span>
        <span>Der.</span>
        <span>Est.</span>
      </div>
      {rev.map((e, idx) => (
        <div key={`${e.frame}-${idx}`} className="frame-log__row bm-caption">
          <span className="bm-mono">{e.frame}</span>
          <span className="bm-mono">{e.leftDeg != null ? `${e.leftDeg.toFixed(0)}°` : '—'}</span>
          <span className="bm-mono">{e.rightDeg != null ? `${e.rightDeg.toFixed(0)}°` : '—'}</span>
          <span
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: statusDot[e.status] ?? statusDot.neutral,
            }}
            title={e.status}
          />
        </div>
      ))}
    </div>
  );
}
