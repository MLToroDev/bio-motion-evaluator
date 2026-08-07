import './StatusBadge.css';

type StatusType = 'connected' | 'disconnected' | 'checking';

interface StatusBadgeProps {
  status: StatusType;
}

const labels: Record<StatusType, string> = {
  connected: 'Backend conectado',
  disconnected: 'Sin conexión',
  checking: 'Comprobando…',
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return <span className={`bm-status-badge bm-status-badge--${status}`}>{labels[status]}</span>;
}
