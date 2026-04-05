import { Fragment } from 'react';
import type { IngestJobDetail } from '../../../../hooks/useDevIngest';

export function JobDetailPanel({ detail }: { detail: IngestJobDetail }) {
  const m = detail.metrics_json || {};
  const perVideo: Array<Record<string, unknown>> = (m.per_video as Array<Record<string, unknown>>) || [];
  return (
    <div className="bm-dev-metrics-panel">
      <div className="bm-label-large" style={{ marginBottom: 'var(--bm-space-sm)' }}>
        Métricas del job
      </div>
      <div className="bm-dev-metrics-row">
        <span>
          Frames leídos: <strong>{m.frames_read ?? '—'}</strong>
        </span>
        <span>
          Features extraídas: <strong>{m.features_extracted ?? '—'}</strong>
        </span>
        <span>
          Muestras insertadas:{' '}
          <strong style={{ color: 'var(--bm-accent)' }}>{m.samples_inserted ?? '—'}</strong>
        </span>
        <span>
          Vídeos procesados: <strong>{m.videos_processed ?? '—'}</strong>
        </span>
        <span>
          Vídeos fallidos:{' '}
          <strong style={{ color: m.videos_failed ? 'var(--bm-angle-bad)' : 'inherit' }}>{m.videos_failed ?? 0}</strong>
        </span>
      </div>
      {perVideo.length > 0 && (
        <>
          <div className="bm-label-large" style={{ marginBottom: 'var(--bm-space-sm)' }}>
            Por vídeo
          </div>
          <div className="bm-dev-per-video-grid">
            <span className="bm-dev-per-video-head">Título</span>
            <span className="bm-dev-per-video-head">Estado</span>
            <span className="bm-dev-per-video-head">Frames</span>
            <span className="bm-dev-per-video-head">Features</span>
            <span className="bm-dev-per-video-head">Muestras</span>
            {perVideo.map((v, i) => (
              <Fragment key={i}>
                <span title={String(v.title || '')} style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {String(v.title || '').slice(0, 60)}
                </span>
                <span style={{ color: v.status === 'ok' ? 'var(--bm-accent)' : 'var(--bm-angle-bad)' }}>
                  {String(v.status || '—')}
                </span>
                <span>{String(v.frames_read ?? '—')}</span>
                <span>{String(v.features_extracted ?? '—')}</span>
                <span>{String(v.samples_inserted ?? '—')}</span>
              </Fragment>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
