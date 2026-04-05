import type { VideoSearchResult } from '../../../../hooks/useDevIngest';
import { fmtDuration } from '../helpers';
import { VideoThumb } from './VideoThumb';

interface VideoCardProps {
  video: VideoSearchResult;
  selected: boolean;
  segCount: number;
  onToggle: () => void;
  onPreview: () => void;
}

export function VideoCard({ video, selected, segCount, onToggle, onPreview }: VideoCardProps) {
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
      </div>

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
