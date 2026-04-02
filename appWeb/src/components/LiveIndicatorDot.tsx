import './ui.css';

export function LiveIndicatorDot({ active }: { active: boolean }) {
  return <span className={`live-dot ${active ? 'live-dot--on' : ''}`} title={active ? 'Conectado' : 'Sin conexión'} />;
}
