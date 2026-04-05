import '../../../components/ui.css';
import { FrameProgressBar } from './FrameProgressBar';
import { ServerHUD } from './ServerHUD';

export interface VideoAnalysisStatsModalProps {
  open: boolean;
  onClose: () => void;
  serverPipelineTotalMs: number | null;
  frameIndex: number;
  totalFrames: number | null;
  qualityFlags: string[];
  progress: number | null;
}

export function VideoAnalysisStatsModal({
  open,
  onClose,
  serverPipelineTotalMs,
  frameIndex,
  totalFrames,
  qualityFlags,
  progress,
}: VideoAnalysisStatsModalProps) {
  if (!open) return null;

  return (
    <div
      className="modal-backdrop"
      role="dialog"
      aria-modal
      aria-labelledby="video-analysis-stats-title"
      onClick={onClose}
    >
      <div
        className="modal-dialog modal-dialog--stats"
        onClick={(e) => e.stopPropagation()}
      >
        <button type="button" className="modal-close-x" onClick={onClose} aria-label="Cerrar">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
        <h2 id="video-analysis-stats-title" className="modal-dialog__title">
          Estadísticas de sesión
        </h2>
        <p className="bm-caption" style={{ margin: '0 0 12px', color: 'var(--bm-text-secondary)' }}>
          Tiempos de pipeline, fotograma actual y avance del archivo en el servidor.
        </p>

        <ServerHUD
          embedded
          serverPipelineTotalMs={serverPipelineTotalMs}
          frameIndex={frameIndex}
          totalFrames={totalFrames}
          qualityFlags={qualityFlags}
        />

        <p
          className="bm-label-large"
          style={{ color: 'var(--bm-text-secondary)', marginTop: 16, marginBottom: 8 }}
        >
          Progreso del vídeo
        </p>
        {progress != null ? (
          <FrameProgressBar progress={progress} frameIndex={frameIndex} totalFrames={totalFrames} />
        ) : (
          <p className="bm-caption" style={{ margin: '8px 0 0', color: 'var(--bm-text-disabled)' }}>
            Sin barra de progreso: inicia un análisis con un vídeo en el servidor para ver el avance por fotograma.
          </p>
        )}
      </div>
    </div>
  );
}
