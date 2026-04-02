import { PoseSkeletonCanvas } from '../../components/PoseSkeletonCanvas';
import {
  FILE_PREVIEW_TIPS,
  type VideoPreviewHudSections,
  VideoPreviewOverlays,
} from '../../components/VideoPreviewOverlays';
import type { LandmarkMap } from '../../lib/poseWsPayload';

interface PreviewCanvasProps {
  previewDataUrl: string | null;
  previewKey: number | string;
  previewAspect: string | number;
  landmarks: LandmarkMap[] | null;
  includePreview: boolean;
  skeletonOnly: boolean;
  running: boolean;
  /** Sub-bloques del HUD (RX, modo, consejos, calidad). */
  hudSections?: VideoPreviewHudSections;
  /** Si false, no se dibuja el canvas de pose 2D sobre el vídeo. */
  skeletonOverlay?: boolean;
  overlayRxPerSec?: number | null;
  overlayQualityFlags?: string[];
  /** Pastilla esquina inferior derecha: FPS efectivos (mensajes/s desde el servidor). */
  showServerFpsPill?: boolean;
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
  hudSections,
  skeletonOverlay = true,
  overlayRxPerSec = null,
  overlayQualityFlags = [],
  showServerFpsPill = true,
  variant = 'aspect',
}: PreviewCanvasProps) {
  const showImage = previewDataUrl && includePreview && !skeletonOnly;
  const showPlaceholder = !previewDataUrl && !landmarks;
  const showHud = running;
  const showSkeleton2d = skeletonOverlay;

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

  const aspectNum =
    typeof previewAspect === 'number' && Number.isFinite(previewAspect) && previewAspect > 0
      ? previewAspect
      : null;

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

      {showSkeleton2d ? (
        <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
          <PoseSkeletonCanvas
            landmarks={landmarks}
            mirrorHorizontal={false}
            contentAspect={imgObjectFit === 'contain' ? aspectNum : null}
          />
        </div>
      ) : null}

      {showServerFpsPill && running && overlayRxPerSec != null ? (
        <div
          aria-live="polite"
          style={{
            position: 'absolute',
            bottom: '0.55rem',
            right: '0.55rem',
            zIndex: 14,
            pointerEvents: 'none',
            background: 'rgba(12, 14, 18, 0.82)',
            backdropFilter: 'blur(8px)',
            WebkitBackdropFilter: 'blur(8px)',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            borderRadius: 'var(--bm-radius-sm)',
            padding: '0.35rem 0.6rem',
            fontFamily: 'var(--bm-font-mono)',
            fontSize: '0.8125rem',
            fontWeight: 600,
            color: 'var(--bm-text-primary)',
            boxShadow: '0 2px 8px rgba(0,0,0,0.35)',
          }}
        >
          <span style={{ fontSize: '0.58rem', fontWeight: 700, letterSpacing: '0.06em', color: 'var(--bm-text-secondary)' }}>
            SERVIDOR{' '}
          </span>
          {overlayRxPerSec.toFixed(1)} FPS
        </div>
      ) : null}

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
        hudSections={hudSections}
        modeLabel="SERVIDOR"
        rxPerSec={overlayRxPerSec}
        rateSuffix="RX/s"
        bullets={FILE_PREVIEW_TIPS}
        qualityFlags={overlayQualityFlags}
      />
    </div>
  );
}
