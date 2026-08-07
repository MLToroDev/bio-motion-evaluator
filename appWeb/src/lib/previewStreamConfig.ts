/**
 * Debe coincidir con `PoseStreamConfig` en `backend/app/models/schemas.py`:
 * - preview_fps: Literal[8, 10, 12]
 * - preview_jpeg_quality: 70..90
 */
export const PREVIEW_FPS_ALLOWED = [8, 10, 12] as const;
export type PreviewFpsAllowed = (typeof PREVIEW_FPS_ALLOWED)[number];

export const PREVIEW_JPEG_QUALITY_MIN = 70;
export const PREVIEW_JPEG_QUALITY_MAX = 90;

export function sanitizePreviewFps(n: number): PreviewFpsAllowed {
  const x = Math.round(Number(n));
  let best: PreviewFpsAllowed = 10;
  let bestD = Infinity;
  for (const v of PREVIEW_FPS_ALLOWED) {
    const d = Math.abs(v - x);
    if (d < bestD) {
      bestD = d;
      best = v;
    }
  }
  return best;
}

export function sanitizePreviewJpegQuality(n: number): number {
  return Math.max(
    PREVIEW_JPEG_QUALITY_MIN,
    Math.min(PREVIEW_JPEG_QUALITY_MAX, Math.round(Number(n))),
  );
}
