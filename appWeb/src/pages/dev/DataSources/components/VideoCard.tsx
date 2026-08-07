import type { IngestVideoUsage, VideoSearchResult } from '../../../../hooks/useDevIngest';
import { fmtDuration } from '../helpers';
import { VideoThumb } from './VideoThumb';

function fmtMetric(n: number | null | undefined): string {
  if (n == null || Number.isNaN(Number(n))) return '—';
  return Number(n).toLocaleString('es-ES');
}

interface VideoCardProps {
  video: VideoSearchResult;
  selected: boolean;
  segCount: number;
  /** Si existe, el vídeo ya apareció en un job de ingesta (badge + métricas del último uso). */
  priorUsage?: IngestVideoUsage | null;
  usageLoading?: boolean;
  onToggle: () => void;
  onPreview: () => void;
}

export function VideoCard({
  video,
  selected,
  segCount,
  priorUsage,
  usageLoading,
  onToggle,
  onPreview,
}: VideoCardProps) {
  return (
    <button
      type="button"
      className={`bm-dev-video-card${selected ? ' bm-dev-video-card--selected' : ''}`}
      onClick={onToggle}
    >
      <div className="bm-dev-video-card__thumb-wrap">
        <VideoThumb youtubeId={video.youtube_id} title={video.title} />

        <span className="bm-dev-video-card__badge" aria-hidden>
          {selected && (
            <svg viewBox="0 0 12 12" className="bm-dev-video-card__badge-check">
              <polyline points="2,6 5,9 10,3" />
            </svg>
          )}
        </span>

        <button
          type="button"
          className="bm-dev-video-card__preview-btn"
          title="Vista previa y segmentos"
          aria-label={`Vista previa: ${video.title}`}
          onClick={(e) => {
            e.stopPropagation();
            onPreview();
          }}
        >
          ▶
        </button>

        {segCount > 0 && (
          <span className="bm-dev-video-card__seg-pill" aria-label={`${segCount} segmentos`}>
            {segCount} seg.
          </span>
        )}

        {priorUsage && (
          <span className="bm-dev-video-card__used-pill" title={`Job ${priorUsage.job_id.slice(0, 8)}… · ${priorUsage.exercise_label}`}>
            Ya usado
          </span>
        )}
      </div>

      <div className="bm-dev-video-card__body">
        <span className="bm-dev-video-card__title">{video.title}</span>
        <span className="bm-dev-video-card__meta">
          {video.channel}
          {video.duration_s ? ` · ${fmtDuration(video.duration_s)}` : ''}
          {video.view_count ? ` · ${(video.view_count / 1000).toFixed(0)}k` : ''}
        </span>
        {usageLoading && !priorUsage ? (
          <span className="bm-dev-video-card__usage bm-dev-video-card__usage--muted">Comprobando historial…</span>
        ) : priorUsage ? (
          <span className="bm-dev-video-card__usage" title={`Estado vídeo: ${priorUsage.video_status ?? '—'}`}>
            <span className="bm-mono">{priorUsage.exercise_label}</span>
            {' · '}
            frames {fmtMetric(priorUsage.frames_read)} · feat. {fmtMetric(priorUsage.features_extracted)} · muestras{' '}
            {fmtMetric(priorUsage.samples_inserted)}
            {priorUsage.video_status && priorUsage.video_status !== 'ok' ? ` · ${priorUsage.video_status}` : ''}
          </span>
        ) : null}
      </div>
      <input type="checkbox" readOnly checked={selected} className="bm-dev-video-card__check" aria-hidden tabIndex={-1} />
    </button>
  );
}
