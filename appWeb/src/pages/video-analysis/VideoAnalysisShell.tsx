import type { ReactNode } from 'react';

interface VideoAnalysisShellProps {
  overlays: ReactNode;
  /** Si es false, el panel lateral no se renderiza y el área principal ocupa todo el ancho. */
  configOpen: boolean;
  onToggleConfig: () => void;
  sidebar: ReactNode;
  mainColumn: ReactNode;
}

/**
 * Chrome de la pantalla: cabecera con toggle de configuración y rejilla adaptable.
 */
export function VideoAnalysisShell({
  overlays,
  configOpen,
  onToggleConfig,
  sidebar,
  mainColumn,
}: VideoAnalysisShellProps) {
  return (
    <div
      style={{
        maxWidth: 1280,
        margin: '0 auto',
        padding: '1.25rem 1.5rem 2rem',
        fontFamily: 'var(--bm-font-body)',
        color: 'var(--bm-text-primary)',
        background: 'var(--bm-background)',
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {overlays}

      <header style={{ marginBottom: '1rem', flexShrink: 0 }}>
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: '0.75rem 1rem',
          }}
        >
          <div style={{ minWidth: 0 }}>
            <h1 className="bm-screen-title" style={{ marginBottom: '0.3rem' }}>
              Análisis de video
            </h1>
            <p className="bm-caption" style={{ margin: 0 }}>
              Gold standard en servidor · REST + WebSocket{' '}
              <code
                style={{
                  fontFamily: 'var(--bm-font-mono)',
                  fontSize: '0.75rem',
                  background: 'var(--bm-surface)',
                  padding: '0.1rem 0.35rem',
                  borderRadius: 4,
                }}
              >
                /ws/pose-stream
              </code>
            </p>
          </div>
          <button
            type="button"
            onClick={onToggleConfig}
            aria-expanded={configOpen}
            aria-controls="video-analysis-config-panel"
            style={{
              flexShrink: 0,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.45rem 0.85rem',
              fontFamily: 'var(--bm-font-body)',
              fontSize: '0.8125rem',
              fontWeight: 600,
              color: 'var(--bm-text-primary)',
              background: 'var(--bm-surface)',
              border: '1px solid var(--bm-border)',
              borderRadius: 'var(--bm-radius-sm)',
              cursor: 'pointer',
            }}
          >
            <span aria-hidden style={{ fontSize: '1rem', lineHeight: 1 }}>
              {configOpen ? '◀' : '▶'}
            </span>
            {configOpen ? 'Ocultar configuración' : 'Mostrar configuración'}
          </button>
        </div>
      </header>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: configOpen ? 'minmax(252px, 288px) minmax(0, 1fr)' : 'minmax(0, 1fr)',
          gap: configOpen ? '1.25rem' : 0,
          alignItems: 'stretch',
          flex: '1 1 auto',
          minHeight: 'calc(100vh - 11.5rem)',
        }}
      >
        {configOpen ? (
          <div
            id="video-analysis-config-panel"
            style={{ minWidth: 0, minHeight: 0, display: 'flex', flexDirection: 'column' }}
          >
            {sidebar}
          </div>
        ) : null}

        <main
          style={{
            minWidth: 0,
            minHeight: 0,
            display: 'flex',
            flexDirection: 'column',
            gap: '0.75rem',
            flex: '1 1 auto',
          }}
        >
          {!configOpen ? (
            <p className="bm-caption" style={{ margin: 0, color: 'var(--bm-text-secondary)' }}>
              Vista ampliada: solo preview y métricas inferiores. Usa «Mostrar configuración» para cambiar vídeo y
              opciones.
            </p>
          ) : null}
          {mainColumn}
        </main>
      </div>
    </div>
  );
}
