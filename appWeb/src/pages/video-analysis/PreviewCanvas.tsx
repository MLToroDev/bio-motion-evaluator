import { PoseSkeletonCanvas } from '../../components/PoseSkeletonCanvas';
import { FILE_PREVIEW_TIPS, VideoPreviewOverlays } from '../../components/VideoPreviewOverlays';
import type { LandmarkMap } from '../../lib/poseWsPayload';

interface PreviewCanvasProps {
  previewDataUrl: string | null;
  previewKey: number | string;
  previewAspect: string | number;
  landmarks: LandmarkMap[] | null;
  includePreview: boolean;
  skeletonOnly: boolean;
  running: boolean;
  /** HUD sobre el vídeo (RX/s, modo, consejos) — solo mientras `running`. */
  overlayRxPerSec?: number | null;
  overlayQualityFlags?: string[];
}

export function PreviewCanvas({
  previewDataUrl,
  previewKey,
  previewAspect,
  landmarks,
  includePreview,
  skeletonOnly,
  running,
  overlayRxPerSec = null,
  overlayQualityFlags = [],
}: PreviewCanvasProps) {
  const showImage = previewDataUrl && includePreview && !skeletonOnly;
  const showPlaceholder = !previewDataUrl && !landmarks;
  const showHud = running;

  const placeholderText = running
    ? 'Esperando fotogramas…'
    : 'Inicia un análisis para ver la vista previa';

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        aspectRatio: String(previewAspect),
        background: '#000',
        borderRadius: 'var(--bm-radius-md)',
        overflow: 'hidden',
        border: '1px solid var(--bm-border)',
        marginTop: '0.5rem',
      }}
    >
      {showImage && (
        <img
          key={previewKey}
          src={previewDataUrl}
          alt="Vista previa del fotograma"
          style={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            objectFit: 'fill',
            display: 'block',
          }}
        />
      )}

      <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
        <PoseSkeletonCanvas landmarks={landmarks} mirrorHorizontal={false} />
      </div>

      {showPlaceholder && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            zIndex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'column',
            gap: '0.5rem',
            color: 'var(--bm-text-disabled)',
            fontFamily: 'var(--bm-font-body)',
            fontSize: '0.875rem',
            textAlign: 'center',
            padding: '1rem',
          }}
        >
          {!running && (
            <svg
              width="32"
              height="32"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <polygon points="23 7 16 12 23 17 23 7" />
              <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
            </svg>
          )}
          <span>{placeholderText}</span>
        </div>
      )}

      <VideoPreviewOverlays
        visible={showHud}
        modeLabel="SERVIDOR"
        rxPerSec={overlayRxPerSec}
        rateSuffix="RX/s"
        bullets={FILE_PREVIEW_TIPS}
        qualityFlags={overlayQualityFlags}
      />
    </div>
  );
}
