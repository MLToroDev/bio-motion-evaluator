import type { CSSProperties } from 'react';

const btnBase: CSSProperties = {
  fontFamily: 'var(--bm-font-body)',
  fontSize: '0.875rem',
  borderRadius: 'var(--bm-radius-sm)',
  cursor: 'pointer',
};

export interface VideoAnalysisActionsProps {
  formValid: boolean;
  running: boolean;
  csvReady: boolean;
  onStart: () => void;
  onStop: () => void;
  onDownloadCsv: () => void;
  /** `panel-footer` — barra fija bajo el scroll del lateral. `main-toolbar` — franja sobre el preview si el lateral está oculto. */
  variant: 'panel-footer' | 'main-toolbar';
}

export function VideoAnalysisActions({
  formValid,
  running,
  csvReady,
  onStart,
  onStop,
  onDownloadCsv,
  variant,
}: VideoAnalysisActionsProps) {
  const isToolbar = variant === 'main-toolbar';

  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '0.5rem',
        alignItems: 'center',
        ...(isToolbar
          ? {
              padding: '0.55rem 0.75rem',
              background: 'var(--bm-surface)',
              border: '1px solid var(--bm-border)',
              borderRadius: 'var(--bm-radius-md)',
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            }
          : {}),
      }}
    >
      {isToolbar ? (
        <span
          style={{
            fontSize: '0.7rem',
            fontWeight: 700,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            color: 'var(--bm-text-disabled)',
            width: '100%',
            marginBottom: '-0.15rem',
          }}
        >
          Análisis
        </span>
      ) : null}
      <button
        type="button"
        disabled={!formValid}
        onClick={onStart}
        style={{
          ...btnBase,
          fontWeight: 700,
          padding: '0.5rem 0.875rem',
          border: '1px solid var(--bm-accent-dim)',
          background: 'var(--bm-accent)',
          color: '#000',
          cursor: formValid ? 'pointer' : 'not-allowed',
          opacity: formValid ? 1 : 0.42,
          transition: 'opacity 120ms',
          flex: isToolbar ? '1 1 140px' : undefined,
        }}
      >
        Iniciar análisis
      </button>

      <button
        type="button"
        disabled={!running}
        onClick={onStop}
        style={{
          ...btnBase,
          padding: '0.5rem 0.875rem',
          border: '1px solid var(--bm-border)',
          background: 'var(--bm-surface-elevated)',
          color: 'var(--bm-text-primary)',
          cursor: running ? 'pointer' : 'not-allowed',
          opacity: running ? 1 : 0.42,
          flex: isToolbar ? '1 1 100px' : undefined,
        }}
      >
        Detener
      </button>

      <button
        type="button"
        disabled={!csvReady}
        onClick={onDownloadCsv}
        style={{
          ...btnBase,
          padding: '0.5rem 0.875rem',
          border: '1px solid var(--bm-border)',
          background: 'transparent',
          color: csvReady ? 'var(--bm-text-secondary)' : 'var(--bm-text-disabled)',
          cursor: csvReady ? 'pointer' : 'not-allowed',
          flex: isToolbar ? '1 1 120px' : undefined,
        }}
      >
        Descargar CSV
      </button>
    </div>
  );
}
