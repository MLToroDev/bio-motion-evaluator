import { BmButton } from '../../../../components/BmButton';
import type { IngestJobItem } from '../../../../hooks/useDevIngest';
import { StatusPill } from './StatusPill';

function num(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return '—';
  return v.toLocaleString('es-ES');
}

/** Barras apiladas: vídeos OK / fallidos / pendientes (estimado). */
function VideoProgressSegments({
  ok,
  fail,
  maxVideos,
  running,
}: {
  ok: number;
  fail: number;
  maxVideos: number;
  running: boolean;
}) {
  const done = ok + fail;
  const cap = Math.max(maxVideos || 1, done, 1);
  const pending = Math.max(0, cap - done);
  const okPct = (ok / cap) * 100;
  const failPct = (fail / cap) * 100;
  const pendPct = (pending / cap) * 100;

  return (
    <div className="bm-dev-ingest-job__video-track" aria-hidden>
      <div
        className="bm-dev-ingest-job__video-seg bm-dev-ingest-job__video-seg--ok"
        style={{ width: `${okPct}%` }}
        title={`${ok} vídeo(s) procesados`}
      />
      <div
        className="bm-dev-ingest-job__video-seg bm-dev-ingest-job__video-seg--fail"
        style={{ width: `${failPct}%` }}
        title={`${fail} fallido(s)`}
      />
      {running && pendPct > 0.5 ? (
        <div
          className="bm-dev-ingest-job__video-seg bm-dev-ingest-job__video-seg--pend"
          style={{ width: `${pendPct}%` }}
          title="Pendiente"
        />
      ) : null}
    </div>
  );
}

/** Mini barras relativas al máximo del propio job (mezcla frames → features → muestras). */
function PipelineBars({
  frames,
  features,
  samples,
}: {
  frames: number;
  features: number;
  samples: number;
}) {
  const max = Math.max(frames, features, samples, 1);
  const rows: { label: string; value: number; cls: string }[] = [
    { label: 'Frames', value: frames, cls: 'bm-dev-ingest-job__pipe--frames' },
    { label: 'Features', value: features, cls: 'bm-dev-ingest-job__pipe--features' },
    { label: 'Muestras', value: samples, cls: 'bm-dev-ingest-job__pipe--samples' },
  ];

  return (
    <div className="bm-dev-ingest-job__pipeline" role="group" aria-label="Rendimiento acumulado del job">
      {rows.map((r) => (
        <div key={r.label} className="bm-dev-ingest-job__pipe-row">
          <span className="bm-dev-ingest-job__pipe-label">{r.label}</span>
          <div className="bm-dev-ingest-job__pipe-track">
            <div
              className={`bm-dev-ingest-job__pipe-fill ${r.cls}`}
              style={{ width: `${Math.min(100, (r.value / max) * 100)}%` }}
            />
          </div>
          <span className="bm-dev-ingest-job__pipe-val bm-mono">{num(r.value)}</span>
        </div>
      ))}
    </div>
  );
}

interface IngestJobCardProps {
  job: IngestJobItem;
  expanded: boolean;
  onToggle: () => void;
}

export function IngestJobCard({ job, expanded, onToggle }: IngestJobCardProps) {
  const vp = job.videos_processed ?? 0;
  const vf = job.videos_failed ?? 0;
  const fr = job.frames_read ?? 0;
  const fx = job.features_extracted ?? 0;
  const sm = job.samples_inserted ?? 0;
  const running = job.status === 'running' || job.status === 'pending';
  const retentionPct =
    fx > 0 && sm >= 0 ? Math.min(100, Math.round((sm / fx) * 1000) / 10) : null;

  return (
    <div
      className={`bm-dev-ingest-job ${running ? 'bm-dev-ingest-job--running' : ''} bm-dev-ingest-job--${job.status}`}
    >
      <BmButton type="button" variant="ghost" className="bm-dev-job-expand bm-dev-ingest-job__hit" onClick={onToggle}>
        <div className="bm-dev-ingest-job__layout">
          <div className="bm-dev-ingest-job__head">
            <div className="bm-dev-ingest-job__title-block">
              <div className="bm-dev-ingest-job__id-row">
                <span className="bm-mono bm-dev-ingest-job__id">{job.id.slice(0, 8)}</span>
                <StatusPill status={job.status} />
                {job.max_videos > 0 ? (
                  <span className="bm-caption bm-dev-ingest-job__meta-pill">
                    hasta {job.max_videos} vídeo{job.max_videos !== 1 ? 's' : ''}
                  </span>
                ) : null}
              </div>
              <div className="bm-dev-ingest-job__query-row">
                <strong className="bm-dev-ingest-job__label">{job.exercise_label}</strong>
                <span className="bm-caption bm-dev-ingest-job__query">{job.query}</span>
              </div>
            </div>
          </div>

          <div className="bm-dev-ingest-job__body">
            <div className="bm-dev-ingest-job__col bm-dev-ingest-job__col--progress">
              <span className="bm-dev-ingest-job__section-h">Vídeos en el lote</span>
              <VideoProgressSegments ok={vp} fail={vf} maxVideos={job.max_videos} running={running} />
              <div className="bm-dev-ingest-job__legend">
                <span>
                  <span className="bm-dev-ingest-job__dot bm-dev-ingest-job__dot--ok" /> OK {num(vp)}
                </span>
                <span>
                  <span className="bm-dev-ingest-job__dot bm-dev-ingest-job__dot--fail" /> Fallos {num(vf)}
                </span>
                {retentionPct != null ? (
                  <span className="bm-dev-ingest-job__retention" title="Muestras / features emitidos">
                    Retención ~{retentionPct}%
                  </span>
                ) : null}
              </div>
            </div>

            <div className="bm-dev-ingest-job__col bm-dev-ingest-job__col--bars">
              <span className="bm-dev-ingest-job__section-h">Rendimiento (acum.)</span>
              <PipelineBars frames={fr} features={fx} samples={sm} />
            </div>
          </div>

          {job.error_message ? (
            <p className="bm-caption bm-dev-ingest-job__err" role="alert">
              {job.error_message}
            </p>
          ) : null}

          <span className="bm-dev-ingest-job__chev" aria-hidden>
            {expanded ? '▲' : '▼'}
          </span>
        </div>
      </BmButton>
    </div>
  );
}
