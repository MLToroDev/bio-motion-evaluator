import type { MetricStatus } from '../lib/metricStatus';
import './ui.css';

export function MetricTile({
  label,
  value,
  sublabel,
  status,
  compact,
}: {
  label: string;
  value: string;
  sublabel?: string | null;
  status: MetricStatus;
  compact?: boolean;
}) {
  const mod =
    status === 'good' ? 'metric-tile--good' : status === 'warn' ? 'metric-tile--warn' : status === 'bad' ? 'metric-tile--bad' : '';
  return (
    <div className={`metric-tile ${compact ? 'compact' : ''} ${mod}`}>
      <div className="metric-tile__label">{label}</div>
      <div className="metric-tile__value">{value}</div>
      {sublabel ? <div className="metric-tile__sublabel">{sublabel}</div> : null}
    </div>
  );
}
