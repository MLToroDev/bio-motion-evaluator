import type { ReactNode } from 'react';

interface VideoAnalysisShellProps {
  overlays: ReactNode;
  sidebar: ReactNode;
  mainColumn: ReactNode;
}

/**
 * Chrome presentacional de la pantalla: contenedor, cabecera y rejilla de dos columnas.
 * La página solo compone este shell con subcomponentes.
 */
export function VideoAnalysisShell({ overlays, sidebar, mainColumn }: VideoAnalysisShellProps) {
  return (
    <div
      style={{
        maxWidth: 1200,
        margin: '0 auto',
        padding: '1.25rem 1.5rem 2rem',
        fontFamily: 'var(--bm-font-body)',
        color: 'var(--bm-text-primary)',
        background: 'var(--bm-background)',
        minHeight: '100vh',
      }}
    >
      {overlays}

      <header style={{ marginBottom: '1.25rem' }}>
        <h1 className="bm-screen-title" style={{ marginBottom: '0.3rem' }}>
          Análisis de video
        </h1>
        <p className="bm-caption">
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
      </header>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(280px, 340px) 1fr',
          gap: '1.5rem',
          alignItems: 'stretch',
        }}
      >
        {sidebar}
        <main style={{ minWidth: 0, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {mainColumn}
        </main>
      </div>
    </div>
  );
}
