import type { PreviewLayerToggleState } from '../../lib/previewLayerPrefs';

const btnBase = {
  fontFamily: 'var(--bm-font-body)',
  fontSize: '0.72rem',
  fontWeight: 600,
  padding: '0.32rem 0.55rem',
  borderRadius: 'var(--bm-radius-sm)',
  cursor: 'pointer' as const,
  border: '1px solid var(--bm-border)',
  transition: 'background 0.15s, border-color 0.15s, color 0.15s',
};

interface PreviewLayerToolbarProps {
  layers: PreviewLayerToggleState;
  onToggle: (key: keyof PreviewLayerToggleState) => void;
}

export function PreviewLayerToolbar({ layers, onToggle }: PreviewLayerToolbarProps) {
  const chip = (key: keyof PreviewLayerToggleState, label: string, title: string) => {
    const on = layers[key];
    return (
      <button
        key={key}
        type="button"
        title={title}
        aria-pressed={on}
        onClick={() => onToggle(key)}
        style={{
          ...btnBase,
          background: on ? 'var(--bm-surface-elevated)' : 'var(--bm-surface)',
          color: on ? 'var(--bm-text-primary)' : 'var(--bm-text-secondary)',
          borderColor: on ? 'var(--bm-accent)' : 'var(--bm-border)',
        }}
      >
        {label}
      </button>
    );
  };

  return (
    <div
      role="group"
      aria-label="Capas sobre la vista previa del vídeo"
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: '0.4rem',
      }}
    >
      <span
        className="bm-caption"
        style={{
          fontSize: '0.68rem',
          fontWeight: 700,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          color: 'var(--bm-text-disabled)',
          marginRight: '0.15rem',
        }}
      >
        Capas
      </span>
      {chip('rate', 'RX/s', 'Mostrar u ocultar la pastilla de tasa RX/s')}
      {chip('mode', 'Modo', 'Mostrar u ocultar la insignia de modo (servidor)')}
      {chip('exercise', 'Ejercicio', 'Clasificación de ejercicio y confianza sobre el vídeo')}
      {chip('tips', 'Consejos', 'Mostrar u ocultar la lista de consejos sobre el vídeo')}
      {chip('quality', 'Calidad', 'Mostrar u ocultar avisos de calidad del servidor')}
      {chip('skeletonOverlay', 'Esqueleto 2D', 'Superponer el esqueleto vectorial sobre el fotograma')}
    </div>
  );
}
