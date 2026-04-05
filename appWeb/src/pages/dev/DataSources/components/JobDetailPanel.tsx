import { Fragment } from 'react';
import type { IngestJobDetail, VideoSearchResult } from '../../../../hooks/useDevIngest';

export function JobDetailPanel({ detail }: { detail: IngestJobDetail }) {
  const m = detail.metrics_json || {};
  const perVideo: Array<Record<string, unknown>> = (m.per_video as Array<Record<string, unknown>>) || [];
  const vids: VideoSearchResult[] = Array.isArray(detail.videos_json) ? detail.videos_json : [];

  const mergedRows = vids.map((vid, i) => {
    const yid = vid.youtube_id;
    const byYid = perVideo.find((p) => String(p.youtube_id || '') === yid);
    const pv = byYid ?? (i < perVideo.length ? perVideo[i] : undefined);
    return { vid, pv: pv ?? {} };
  });

  return (
    <div className="bm-dev-metrics-panel">
      {mergedRows.length > 0 ? (
        <>
          <div className="bm-label-large" style={{ marginBottom: 'var(--bm-space-sm)' }}>
            Vídeos de este análisis
          </div>
          <p className="bm-caption" style={{ marginTop: 0, marginBottom: 'var(--bm-space-md)' }}>
            Lote devuelto por la búsqueda del job ({mergedRows.length} vídeo{mergedRows.length !== 1 ? 's' : ''}
            ). Consulta con las métricas por vídeo inferidas al procesar.
          </p>
          <ul className="bm-dev-job-video-list">
            {mergedRows.map(({ vid, pv }) => (
              <li key={vid.youtube_id} className="bm-dev-job-video-list__item">
                <span className="bm-mono bm-dev-job-video-list__id" title={vid.youtube_id}>
                  {vid.youtube_id}
                </span>
                <span className="bm-dev-job-video-list__title" title={vid.title}>
                  {vid.title}
                </span>
                <span
                  className={`bm-dev-job-video-list__st ${pv.status === 'ok' ? 'bm-dev-job-video-list__st--ok' : ''}`}
                >
                  {String(pv.status ?? '—')}
                </span>
                <span className="bm-dev-job-video-list__nums">
                  f {pv.frames_read != null ? String(pv.frames_read) : '—'} · feat.{' '}
                  {pv.features_extracted != null ? String(pv.features_extracted) : '—'} · muestras{' '}
                  {pv.samples_inserted != null ? String(pv.samples_inserted) : '—'}
                </span>
              </li>
            ))}
          </ul>
        </>
      ) : null}

      <div className="bm-label-large" style={{ marginBottom: 'var(--bm-space-sm)', marginTop: 'var(--bm-space-md)' }}>
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
            Por vídeo (tabla)
          </div>
          <div className="bm-dev-per-video-grid bm-dev-per-video-grid--with-id">
            <span className="bm-dev-per-video-head">YouTube</span>
            <span className="bm-dev-per-video-head">Título</span>
            <span className="bm-dev-per-video-head">Estado</span>
            <span className="bm-dev-per-video-head">Frames</span>
            <span className="bm-dev-per-video-head">Features</span>
            <span className="bm-dev-per-video-head">Muestras</span>
            {perVideo.map((v, i) => (
              <Fragment key={i}>
                <span className="bm-mono" title={String(v.youtube_id || '')}>
                  {String(v.youtube_id || '—').slice(0, 11)}
                </span>
                <span title={String(v.title || '')} style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {String(v.title || '').slice(0, 48)}
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
