import { BmButton } from '../../../components/BmButton';
import { BmInput, BmSelect } from '../../../components/BmInput';
import '../devPages.css';
import { IngestJobCard } from './components/IngestJobCard';
import { JobDetailPanel } from './components/JobDetailPanel';
import { VideoCard } from './components/VideoCard';
import { VideoPreviewModal } from './components/VideoPreviewModal';
import { useDataSources } from './hooks/useDataSources';

const EXERCISE_LABELS = [
  'idle',
  'squat',
  'lunge',
  'curl',
  'running',
  'pushup',
  'plank',
  'jumping_jack',
  'overhead_press',
  'deadlift',
  'mountain_climber',
];

export default function DataSources() {
  const {
    searching,
    searchError,
    searchResults,
    jobs,
    jobsError,
    loadJobs,
    creating,
    createError,
    searchQ,
    setSearchQ,
    selectedLabel,
    setSelectedLabel,
    selected,
    setSelected,
    autoApprove,
    setAutoApprove,
    onlyWindowFull,
    setOnlyWindowFull,
    requirePoseOk,
    setRequirePoseOk,
    emitEvery,
    setEmitEvery,
    expandedJobId,
    expandedDetail,
    videoSegments,
    setVideoSegments,
    previewVideo,
    setPreviewVideo,
    handleSearch,
    handleSelectAll,
    handleIngest,
    toggleJobDetail,
    videoUsageById,
    usageLoading,
    usageError,
  } = useDataSources();

  return (
    <div className="bm-dev-page">
      <h1 className="bm-screen-title">Fuentes de datos</h1>
      <p className="bm-caption" style={{ maxWidth: 620, marginBottom: 'var(--bm-space-lg)' }}>
        Busca vídeos de ejercicios en YouTube, selecciona los que quieres procesar y encola la ingesta automática. Cada vídeo se
        descarga, se extraen vectores 32D con MediaPipe y se insertan como muestras en el dataset.
        Usa el botón&nbsp;▶ de cada tarjeta para ver el vídeo y definir qué tramos debe analizar la IA.
      </p>

      {selected.size > 0 && (
        <section className="bm-dev-section bm-dev-section--accent bm-dev-ingest-sticky">
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
        {usageError ? <p className="bm-caption bm-dev-msg--error">Historial de uso: {usageError}</p> : null}

        {searchResults.length > 0 && (
          <div>
            <div className="bm-dev-results-bar">
              <span className="bm-caption">
                {searchResults.length} resultados — {selected.size} seleccionados
                {usageLoading ? ' — comprobando si ya se usaron en ingestas…' : ''}
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
                  segCount={(videoSegments[v.youtube_id] ?? []).length}
                  priorUsage={videoUsageById[v.youtube_id] ?? null}
                  usageLoading={usageLoading}
                  onToggle={() => {
                    const n = new Set(selected);
                    if (n.has(i)) n.delete(i);
                    else n.add(i);
                    setSelected(n);
                  }}
                  onPreview={() => setPreviewVideo(v)}
                />
              ))}
            </div>
          </div>
        )}
      </section>

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
        <div className="bm-dev-ingest-job-list">
          {jobs.map((job) => (
            <div key={job.id} className="bm-dev-job-shell">
              <IngestJobCard
                job={job}
                expanded={expandedJobId === job.id}
                onToggle={() => void toggleJobDetail(job.id)}
              />
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

      {previewVideo && (
        <VideoPreviewModal
          video={previewVideo}
          segments={videoSegments[previewVideo.youtube_id] ?? []}
          onSegmentsChange={(segs) =>
            setVideoSegments((prev) => ({ ...prev, [previewVideo.youtube_id]: segs }))
          }
          onClose={() => setPreviewVideo(null)}
        />
      )}
    </div>
  );
}
