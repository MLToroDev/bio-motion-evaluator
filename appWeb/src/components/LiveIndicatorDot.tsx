import './LiveIndicatorDot.css';

interface LiveIndicatorDotProps {
  active: boolean;
}

export function LiveIndicatorDot({ active }: LiveIndicatorDotProps) {
  return (
    <span
      className={`bm-live-dot ${active ? 'bm-live-dot--active' : ''}`}
      aria-label={active ? 'Sesión activa' : 'Inactivo'}
      role="status"
    />
  );
}
