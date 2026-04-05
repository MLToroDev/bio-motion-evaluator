import { Fragment, useState } from 'react';
import { BmButton } from '../../components/BmButton';
import { BmInput, BmSelect } from '../../components/BmInput';
import { useDevIngest, type IngestJobDetail, type VideoSearchResult } from '../../hooks/useDevIngest';
import './devPages.css';

const EXERCISE_LABELS = ['idle', 'squat', 'lunge'];

function fmtDuration(s: number): string {
  if (!s) return '—';
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${sec.toString().padStart(2, '0')}`;
}

function StatusPill({ status }: { status: string }) {
  const color =
    status === 'completed'
      ? 'var(--bm-accent)'
      : status === 'running'
        ? 'var(--bm-angle-warn)'
        : status === 'failed'
          ? 'var(--bm-angle-bad)'
          : 'var(--bm-text-secondary)';
  return (
    <span className="bm-caption" style={{ color, fontWeight: 600 }}>
      {status}
    </span>
  );
}

/** Thumbnail con fallback: usa proxy de imagen de yt-img.com para evitar el bloqueo CORS
 *  de YouTube cuando se carga desde localhost/dominio distinto. */
function VideoThumb({ url, title }: { url: string; title: string }) {
  const [failed, setFailed] = useState(false);
  if (!url || failed) {
    return (
      <div className="bm-dev-video-card__thumb-placeholder" aria-hidden>
        🎬
      </div>
    );
  }
  return (
    <img
      src={url}
      alt={title}
      className="bm-dev-video-card__thumb"
      crossOrigin="anonymous"
      onError={() => setFailed(true)}
      loading="lazy"
    />
  );
}

function VideoCard({
  video,
  selected,
  onToggle,
}: {
  video: VideoSearchResult;
  selected: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      className={`bm-dev-video-card${selected ? ' bm-dev-video-card--selected' : ''}`}
      onClick={onToggle}
    >
      {/* Thumbnail 16:9 */}
      <div className="bm-dev-video-card__thumb-wrap">
        <VideoThumb url={video.thumbnail_url} title={video.title} />
        {/* Badge de selección */}
        <span className="bm-dev-video-card__badge" aria-hidden>
          {selected && (
            <svg viewBox="0 0 12 12" className="bm-dev-video-card__badge-check">
              <polyline points="2,6 5,9 10,3" />
            </svg>
          )}
        </span>
      </div>
      {/* Info */}
      <div className="bm-dev-video-card__body">
        <span className="bm-dev-video-card__title">{video.title}</span>
        <span className="bm-dev-video-card__meta">
          {video.channel}
          {video.duration_s ? ` · ${fmtDuration(video.duration_s)}` : ''}
          {video.view_count ? ` · ${(video.view_count / 1000).toFixed(0)}k` : ''}
        </span>
      </div>
      <input type="checkbox" readOnly checked={selected} className="bm-dev-video-card__check" aria-hidden tabIndex={-1} />
    </button>
  );
}

function JobDetailPanel({ detail }: { detail: IngestJobDetail }) {
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

export default function DataSourcesPage() {
  const {
    searching,
    searchError,
    searchResults,
    searchYoutube,
    jobs,
    jobsError,
    loadJobs,
    creating,
    createError,
    createIngestJob,
    getJobDetail,
  } = useDevIngest();

  const [searchQ, setSearchQ] = useState('');
  const [selectedLabel, setSelectedLabel] = useState('squat');
  const [selected, setSelected] = useState<Set<number>>(() => new Set());
  const [maxVideos] = useState(5);
  const [autoApprove, setAutoApprove] = useState(false);
  const [onlyWindowFull, setOnlyWindowFull] = useState(true);
  const [requirePoseOk, setRequirePoseOk] = useState(true);
  const [emitEvery, setEmitEvery] = useState(3);
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);
  const [expandedDetail, setExpandedDetail] = useState<IngestJobDetail | null>(null);

  const handleSearch = () => {
    const q = searchQ.trim();
    if (!q) return;
    setSelected(new Set());
    void searchYoutube(q, maxVideos + 5);
  };

  const handleSelectAll = () => {
    if (selected.size === searchResults.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(searchResults.map((_, i) => i)));
    }
  };

  const handleIngest = async () => {
    const videos = searchResults.filter((_, i) => selected.has(i));
    if (videos.length === 0) return;
    const ok = await createIngestJob({
      label: selectedLabel,
      query: searchQ.trim() || selectedLabel,
      max_videos: videos.length,
      auto_approve: autoApprove,
      only_window_full: onlyWindowFull,
      require_pose_ok: requirePoseOk,
      emit_every: emitEvery,
    });
    if (ok) setSelected(new Set());
  };

  const toggleJobDetail = async (id: string) => {
    if (expandedJobId === id) {
      setExpandedJobId(null);
      setExpandedDetail(null);
    } else {
      setExpandedJobId(id);
      setExpandedDetail(null);
      const detail = await getJobDetail(id);
      setExpandedDetail(detail);
    }
  };

  return (
    <div className="bm-dev-page" style={{ maxWidth: 860 }}>
      <h1 className="bm-screen-title">Fuentes de datos</h1>
      <p className="bm-caption" style={{ maxWidth: 620, marginBottom: 'var(--bm-space-lg)' }}>
        Busca vídeos de ejercicios en YouTube, selecciona los que quieres procesar y encola la ingesta automática. Cada vídeo se
        descarga, se extraen vectores 32D con MediaPipe y se insertan como muestras en el dataset.
      </p>

      <section className="bm-dev-section">
        <div className="bm-dev-search-row">
          <div className="bm-dev-search-row__grow">
            <BmInput
              label="Búsqueda"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              placeholder="ej. sentadilla profunda, squat tutorial…"
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              autoComplete="off"
            />
          </div>
          <div className="bm-dev-search-row__field-fixed">
            <BmSelect label="Etiqueta" value={selectedLabel} onChange={(e) => setSelectedLabel(e.target.value)}>
              {EXERCISE_LABELS.map((l) => (
                <option key={l} value={l}>
                  {l}
                </option>
              ))}
            </BmSelect>
          </div>
          <BmButton type="button" variant="primary" disabled={searching || !searchQ.trim()} onClick={handleSearch} loading={searching}>
            Buscar en YouTube
          </BmButton>
        </div>
        {searchError ? <p className="bm-caption bm-dev-msg--error">{searchError}</p> : null}

        {searchResults.length > 0 && (
          <div>
            <div className="bm-dev-results-bar">
              <span className="bm-caption">
                {searchResults.length} resultados — {selected.size} seleccionados
              </span>
              <BmButton type="button" variant="ghost" onClick={handleSelectAll}>
                {selected.size === searchResults.length ? 'Deseleccionar todo' : 'Seleccionar todo'}
              </BmButton>
            </div>
            <div className="bm-dev-video-stack">
              {searchResults.map((v, i) => (
                <VideoCard
                  key={v.youtube_id || i}
                  video={v}
                  selected={selected.has(i)}
                  onToggle={() => {
                    const n = new Set(selected);
                    if (n.has(i)) n.delete(i);
                    else n.add(i);
                    setSelected(n);
                  }}
                />
              ))}
            </div>
          </div>
        )}
      </section>

      {selected.size > 0 && (
        <section className="bm-dev-section bm-dev-section--accent">
          <div className="bm-dev-ingest-title">
            Ingestar {selected.size} vídeo{selected.size > 1 ? 's' : ''} como «{selectedLabel}»
          </div>
          {createError ? <p className="bm-caption bm-dev-msg--error">{createError}</p> : null}
          <div className="bm-dev-ingest-options">
            <label className="bm-dev-check">
              <input type="checkbox" checked={autoApprove} onChange={(e) => setAutoApprove(e.target.checked)} />
              Aprobar muestras automáticamente
            </label>
            <label className="bm-dev-check">
              <input type="checkbox" checked={onlyWindowFull} onChange={(e) => setOnlyWindowFull(e.target.checked)} />
              Solo ventana llena (recomendado)
            </label>
            <label className="bm-dev-check">
              <input type="checkbox" checked={requirePoseOk} onChange={(e) => setRequirePoseOk(e.target.checked)} />
              Requiere pose_ok
            </label>
            <label className="bm-dev-emit-inline">
              Emitir cada
              <input
                type="number"
                className="bm-field__input"
                min={1}
                max={30}
                value={emitEvery}
                onChange={(e) => setEmitEvery(Math.max(1, parseInt(e.target.value, 10) || 1))}
              />
              frames
            </label>
          </div>
          <BmButton type="button" variant="primary" disabled={creating} loading={creating} onClick={() => void handleIngest()}>
            Encolar ingesta
          </BmButton>
        </section>
      )}

      <section>
        <div className="bm-dev-results-bar" style={{ marginBottom: 'var(--bm-space-md)' }}>
          <h2 className="bm-section-title" style={{ margin: 0 }}>
            Historial de ingestas
          </h2>
          <BmButton type="button" variant="outline" onClick={() => void loadJobs()}>
            Refrescar
          </BmButton>
        </div>
        {jobsError ? <p className="bm-caption bm-dev-msg--error">{jobsError}</p> : null}
        {jobs.length === 0 ? <p className="bm-caption">Sin jobs de ingesta aún.</p> : null}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--bm-space-sm)' }}>
          {jobs.map((job) => (
            <div key={job.id} className="bm-dev-job-shell">
              <BmButton type="button" variant="ghost" className="bm-dev-job-expand" onClick={() => void toggleJobDetail(job.id)}>
                <div style={{ display: 'flex', gap: 'var(--bm-space-md)', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                  <div className="bm-body" style={{ margin: 0 }}>
                    <span className="bm-mono">{job.id.slice(0, 8)}</span>
                    <span style={{ margin: '0 var(--bm-space-sm)', opacity: 0.5 }}>·</span>
                    <strong>{job.exercise_label}</strong>
                    <span style={{ margin: '0 var(--bm-space-sm)', opacity: 0.5 }}>·</span>
                    <span style={{ color: 'var(--bm-text-secondary)' }}>{job.query}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 'var(--bm-space-md)', alignItems: 'center', flexWrap: 'wrap', fontSize: '0.8125rem' }}>
                    <StatusPill status={job.status} />
                    {job.samples_inserted != null && (
                      <span style={{ color: 'var(--bm-accent)' }}>{job.samples_inserted} muestras</span>
                    )}
                    {job.videos_processed != null && <span>{job.videos_processed} vídeos</span>}
                    {job.error_message && (
                      <span className="bm-caption" style={{ color: 'var(--bm-angle-bad)', maxWidth: 300 }}>
                        {job.error_message.slice(0, 80)}
                      </span>
                    )}
                  </div>
                </div>
              </BmButton>
              {expandedJobId === job.id && (
                <div className="bm-dev-job-detail">
                  {expandedDetail ? (
                    <JobDetailPanel detail={expandedDetail} />
                  ) : (
                    <p className="bm-caption">Cargando…</p>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
