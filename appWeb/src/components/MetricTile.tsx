import type { MetricStatus } from '../lib/metricStatus';
import './MetricTile.css';

const statusColorMap: Record<MetricStatus, string> = {
  good: 'var(--bm-angle-good)',
  warn: 'var(--bm-angle-warn)',
  bad: 'var(--bm-angle-bad)',
  neutral: 'var(--bm-text-secondary)',
};

export function MetricTile({
  label,
  value,
  status = 'neutral',
  sublabel,
  compact,
}: {
  label: string;
  value: string;
  sublabel?: string | null;
  status?: MetricStatus;
  compact?: boolean;
}) {
  const short = label.length > 12 ? `${label.slice(0, 12)}...` : label;
  const mod = status === 'bad' ? 'bm-metric-tile--bad' : '';
  return (
    <div className={`bm-metric-tile ${mod} ${compact ? 'bm-metric-tile--compact' : ''}`}>
      <span className="bm-metric-tile__label">{short.toUpperCase()}</span>
      <span
        className={`bm-metric-tile__value ${compact ? 'bm-metric-md' : 'bm-metric-lg'}`}
        style={{ color: statusColorMap[status] }}
      >
        {value}
      </span>
      {sublabel ? <span className="bm-metric-tile__sublabel bm-caption">{sublabel}</span> : null}
    </div>
  );
}
