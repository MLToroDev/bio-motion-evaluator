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
  overlayRxPerSec?: number | null;
  overlayQualityFlags?: string[];
  /**
   * `hero` — área principal: crece en altura, `object-fit: contain` en el JPEG.
   * `aspect` — tamaño fijo según relación de aspecto del stream.
   */
  variant?: 'hero' | 'aspect';
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
  variant = 'aspect',
}: PreviewCanvasProps) {
  const showImage = previewDataUrl && includePreview && !skeletonOnly;
  const showPlaceholder = !previewDataUrl && !landmarks;
  const showHud = running;

  const placeholderText = running
    ? 'Esperando fotogramas…'
    : 'Inicia un análisis para ver la vista previa';

  const isHero = variant === 'hero';

  const rootStyle = isHero
    ? {
        position: 'relative' as const,
        width: '100%',
        flex: '1 1 auto',
        minHeight: 'clamp(280px, 52vh, 760px)',
        maxHeight: 'min(78vh, 880px)',
        background: '#000',
        borderRadius: 'var(--bm-radius-md)',
        overflow: 'hidden',
        border: '1px solid var(--bm-border)',
      }
    : {
        position: 'relative' as const,
        width: '100%',
        aspectRatio: String(previewAspect),
        background: '#000',
        borderRadius: 'var(--bm-radius-md)',
        overflow: 'hidden',
        border: '1px solid var(--bm-border)',
        marginTop: '0.5rem',
      };

  const imgObjectFit = isHero ? 'contain' : 'fill';

  return (
    <div style={rootStyle}>
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
            objectFit: imgObjectFit,
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
