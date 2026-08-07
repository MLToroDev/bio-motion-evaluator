import { useEffect, useRef, type RefObject } from 'react';
import { lerpLandmarksInto } from '../lib/landmarkInterpolation';
import { POSE_CONNECTIONS } from '../lib/poseTopology';
import type { LandmarkMap } from '../lib/poseWsPayload';

const MIN_VIS = 0.4;

const SKELETON_TOKEN_FALLBACKS = {
  line: '#00e676',
  joint: '#ffffff',
  jointBorder: '#00e676',
} as const;

export type SkeletonStyleCache = {
  lineRgb: string;
  jointFill: string;
  jointStroke: string;
};

function readSkeletonStyleCache(): SkeletonStyleCache {
  if (typeof document === 'undefined') {
    return {
      lineRgb: hexToRgba(SKELETON_TOKEN_FALLBACKS.line, 0.85),
      jointFill: SKELETON_TOKEN_FALLBACKS.joint,
      jointStroke: hexToRgba(SKELETON_TOKEN_FALLBACKS.jointBorder, 0.35),
    };
  }
  const computed = getComputedStyle(document.documentElement);
  const line =
    computed.getPropertyValue('--bm-skeleton-line').trim() || SKELETON_TOKEN_FALLBACKS.line;
  const joint =
    computed.getPropertyValue('--bm-skeleton-joint').trim() || SKELETON_TOKEN_FALLBACKS.joint;
  const jointBorder =
    computed.getPropertyValue('--bm-skeleton-joint-border').trim() ||
    SKELETON_TOKEN_FALLBACKS.jointBorder;
  return {
    lineRgb: line.startsWith('#') ? hexToRgba(line, 0.85) : line,
    jointFill: joint,
    jointStroke: hexToRgba(jointBorder, 0.35),
  };
}

function hexToRgba(hex: string, alpha: number): string {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim());
  if (!m) return hex;
  const n = parseInt(m[1], 16);
  const r = (n >> 16) & 255;
  const g = (n >> 8) & 255;
  const b = n & 255;
  return `rgba(${r},${g},${b},${alpha})`;
}

/** Rectángulo donde vive el vídeo con ``object-fit: contain`` (width/height del contenido). */
function videoContentRect(
  cw: number,
  ch: number,
  aspectWidthOverHeight: number | null | undefined,
): { ox: number; oy: number; dw: number; dh: number } {
  if (
    aspectWidthOverHeight == null ||
    !Number.isFinite(aspectWidthOverHeight) ||
    aspectWidthOverHeight <= 0
  ) {
    return { ox: 0, oy: 0, dw: cw, dh: ch };
  }
  const ar = aspectWidthOverHeight;
  if (cw / ch > ar) {
    const dh = ch;
    const dw = dh * ar;
    return { ox: (cw - dw) / 2, oy: 0, dw, dh };
  }
  const dw = cw;
  const dh = dw / ar;
  return { ox: 0, oy: (ch - dh) / 2, dw, dh };
}

function landmarkPoint(
  lm: LandmarkMap,
  ox: number,
  oy: number,
  dw: number,
  dh: number,
  mirror: boolean,
): { x: number; y: number } | null {
  const i = lm.index;
  if (typeof i !== 'number') return null;
  const vis = lm.visibility;
  if (typeof vis === 'number' && vis < MIN_VIS) return null;
  const x = lm.x;
  const y = lm.y;
  if (typeof x !== 'number' || typeof y !== 'number') return null;
  const nx = mirror ? 1 - x : x;
  return { x: ox + nx * dw, y: oy + y * dh };
}

function drawSkeleton(
  canvas: HTMLCanvasElement,
  wrap: HTMLDivElement,
  lm: LandmarkMap[] | null,
  mirror: boolean,
  contentAspect: number | null | undefined,
  styles: SkeletonStyleCache,
) {
  const dpr = window.devicePixelRatio || 1;
  const { clientWidth: cw, clientHeight: ch } = wrap;
  if (cw < 2 || ch < 2) return;

  canvas.width = Math.round(cw * dpr);
  canvas.height = Math.round(ch * dpr);
  canvas.style.width = `${cw}px`;
  canvas.style.height = `${ch}px`;

  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cw, ch);

  if (!lm || lm.length === 0) return;

  const { ox, oy, dw, dh } = videoContentRect(cw, ch, contentAspect);

  const points = new Map<number, { x: number; y: number }>();
  for (const m of lm) {
    const i = m.index;
    if (typeof i !== 'number') continue;
    const p = landmarkPoint(m, ox, oy, dw, dh, mirror);
    if (p) points.set(i, p);
  }

  ctx.strokeStyle = styles.lineRgb;
  ctx.lineWidth = 2;
  ctx.lineCap = 'round';
  for (const [a, b] of POSE_CONNECTIONS) {
    const pa = points.get(a);
    const pb = points.get(b);
    if (!pa || !pb) continue;
    ctx.beginPath();
    ctx.moveTo(pa.x, pa.y);
    ctx.lineTo(pb.x, pb.y);
    ctx.stroke();
  }

  ctx.fillStyle = styles.jointFill;
  ctx.strokeStyle = styles.jointStroke;
  for (const p of points.values()) {
    ctx.beginPath();
    ctx.arc(p.x, p.y, 3.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
  }
}

function snapshotLandmarks(source: LandmarkMap[]): LandmarkMap[] {
  return source.map((m) => ({ ...m }));
}

let warnedLandmarksRefWithoutSmooth = false;

/**
 * Overlay 2D de pose.
 *
 * Invariantes:
 * - `landmarksRef` solo con `smoothMotion === true` (análisis en vivo).
 * - Con `smoothMotion === false`, usar `landmarks` (p. ej. PreviewCanvas).
 */
export function PoseSkeletonCanvas({
  landmarks = null,
  landmarksRef,
  mirrorHorizontal = false,
  contentAspect,
  smoothMotion = false,
}: {
  landmarks?: LandmarkMap[] | null;
  landmarksRef?: RefObject<LandmarkMap[] | null>;
  mirrorHorizontal?: boolean;
  contentAspect?: number | null;
  smoothMotion?: boolean;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const targetRef = useRef<LandmarkMap[] | null>(null);
  const fromRef = useRef<LandmarkMap[] | null>(null);
  const displayBufferRef = useRef<LandmarkMap[]>([]);
  const blendStartRef = useRef(0);
  const adaptiveBlendMsRef = useRef(120);
  const lastPoseTimestampRef = useRef(performance.now());
  const lastSeenRef = useRef<LandmarkMap[] | null>(null);
  const mirrorRef = useRef(mirrorHorizontal);
  const aspectRef = useRef(contentAspect);
  const styleCacheRef = useRef<SkeletonStyleCache>(readSkeletonStyleCache());

  mirrorRef.current = mirrorHorizontal;
  aspectRef.current = contentAspect;

  useEffect(() => {
    styleCacheRef.current = readSkeletonStyleCache();
  }, []);

  useEffect(() => {
    if (!smoothMotion && landmarksRef != null && import.meta.env.DEV && !warnedLandmarksRefWithoutSmooth) {
      warnedLandmarksRefWithoutSmooth = true;
      console.warn(
        '[PoseSkeletonCanvas] landmarksRef se ignora cuando smoothMotion=false; use landmarks.',
      );
    }
  }, [smoothMotion, landmarksRef]);

  // Rama legacy: smoothMotion + landmarks prop (sin ref)
  useEffect(() => {
    if (!smoothMotion || landmarksRef != null) return;

    if (!landmarks || landmarks.length === 0) {
      targetRef.current = null;
      fromRef.current = null;
      displayBufferRef.current = [];
      return;
    }

    const now = performance.now();
    const interval = now - lastPoseTimestampRef.current;
    if (interval > 0 && interval < 500) {
      adaptiveBlendMsRef.current = Math.max(80, interval * 0.9);
    }
    lastPoseTimestampRef.current = now;

    fromRef.current =
      displayBufferRef.current.length > 0
        ? snapshotLandmarks(displayBufferRef.current)
        : snapshotLandmarks(landmarks);
    targetRef.current = landmarks;
    blendStartRef.current = now;
  }, [landmarks, smoothMotion, landmarksRef]);

  useEffect(() => {
    if (smoothMotion) return;
    const canvas = canvasRef.current;
    const wrap = wrapRef.current;
    if (!canvas || !wrap) return;

    const paint = (lm: LandmarkMap[] | null) => {
      drawSkeleton(canvas, wrap, lm, mirrorRef.current, aspectRef.current, styleCacheRef.current);
    };

    paint(landmarks ?? null);
    const ro = new ResizeObserver(() => paint(landmarks ?? null));
    ro.observe(wrap);
    return () => ro.disconnect();
  }, [landmarks, smoothMotion]);

  useEffect(() => {
    if (!smoothMotion) return;

    const canvas = canvasRef.current;
    const wrap = wrapRef.current;
    if (!canvas || !wrap) return;

    const paint = (lm: LandmarkMap[] | null) => {
      drawSkeleton(canvas, wrap, lm, mirrorRef.current, aspectRef.current, styleCacheRef.current);
    };

    const liveRef = landmarksRef;
    const liveMode = landmarksRef != null;

    let rafId = 0;

    const tick = () => {
      if (liveMode && liveRef) {
        const incoming = liveRef.current;

        if (incoming === null) {
          if (lastSeenRef.current !== null) {
            targetRef.current = null;
            fromRef.current = null;
            displayBufferRef.current = [];
            lastSeenRef.current = null;
            paint(null);
          }
          rafId = requestAnimationFrame(tick);
          return;
        }

        if (incoming !== lastSeenRef.current) {
          const now = performance.now();
          const interval = now - lastPoseTimestampRef.current;
          if (interval > 0 && interval < 500) {
            adaptiveBlendMsRef.current = Math.max(80, interval * 0.9);
          }
          lastPoseTimestampRef.current = now;

          fromRef.current =
            displayBufferRef.current.length > 0
              ? snapshotLandmarks(displayBufferRef.current)
              : snapshotLandmarks(incoming);
          targetRef.current = incoming;
          blendStartRef.current = now;
          lastSeenRef.current = incoming;
        }

        const target = targetRef.current;
        if (target && target.length > 0) {
          const elapsed = performance.now() - blendStartRef.current;
          const linear = Math.min(1, elapsed / adaptiveBlendMsRef.current);
          const eased = linear * (2 - linear);
          lerpLandmarksInto(fromRef.current, target, eased, displayBufferRef.current);
          paint(displayBufferRef.current);
        } else {
          paint(null);
        }
      } else {
        const target = targetRef.current;
        if (target && target.length > 0) {
          const elapsed = performance.now() - blendStartRef.current;
          const linear = Math.min(1, elapsed / adaptiveBlendMsRef.current);
          const eased = linear * (2 - linear);
          lerpLandmarksInto(fromRef.current, target, eased, displayBufferRef.current);
          paint(displayBufferRef.current);
        } else {
          paint(null);
        }
      }

      rafId = requestAnimationFrame(tick);
    };

    rafId = requestAnimationFrame(tick);

    const ro = new ResizeObserver(() => {
      const lm = displayBufferRef.current.length > 0 ? displayBufferRef.current : null;
      paint(lm);
    });
    ro.observe(wrap);
    return () => {
      cancelAnimationFrame(rafId);
      ro.disconnect();
    };
  }, [smoothMotion]);

  return (
    <div ref={wrapRef} className="pose-canvas-wrap">
      <canvas ref={canvasRef} className="pose-canvas" aria-hidden />
    </div>
  );
}
