import { useEffect, useRef, type RefObject } from 'react';

/** Objeto detectado por el backend (bbox normalizado 0–1). */
export type DetectedObjectBox = {
  label: string;
  label_es?: string;
  confidence: number;
  /** [x1, y1, x2, y2] en coords normalizadas del frame. */
  bbox_norm: [number, number, number, number];
  equipment_slug?: string | null;
};

const COLORS = [
  '#f59e0b',
  '#22d3ee',
  '#a78bfa',
  '#34d399',
  '#fb7185',
  '#fbbf24',
];

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

function drawBoxes(
  canvas: HTMLCanvasElement,
  wrap: HTMLDivElement,
  objects: DetectedObjectBox[] | null,
  mirror: boolean,
  contentAspect: number | null | undefined,
) {
  const rect = wrap.getBoundingClientRect();
  const cw = Math.max(1, Math.round(rect.width));
  const ch = Math.max(1, Math.round(rect.height));
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  canvas.width = Math.round(cw * dpr);
  canvas.height = Math.round(ch * dpr);
  canvas.style.width = `${cw}px`;
  canvas.style.height = `${ch}px`;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cw, ch);
  if (!objects || objects.length === 0) return;

  const { ox, oy, dw, dh } = videoContentRect(cw, ch, contentAspect);
  ctx.lineWidth = 2;
  ctx.font = '600 12px var(--bm-font-body, system-ui, sans-serif)';
  ctx.textBaseline = 'top';

  objects.forEach((obj, i) => {
    const bb = obj.bbox_norm;
    if (!bb || bb.length < 4) return;
    let [x1, y1, x2, y2] = bb;
    if (mirror) {
      const nx1 = 1 - x2;
      const nx2 = 1 - x1;
      x1 = nx1;
      x2 = nx2;
    }
    const px = ox + x1 * dw;
    const py = oy + y1 * dh;
    const pw = Math.max(2, (x2 - x1) * dw);
    const ph = Math.max(2, (y2 - y1) * dh);
    const color = COLORS[i % COLORS.length];
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.strokeRect(px, py, pw, ph);

    const title = obj.label_es || obj.label || 'objeto';
    const pct = Math.round(Math.min(100, Math.max(0, obj.confidence * 100)));
    const text = `${title} ${pct}%`;
    const padX = 6;
    const padY = 3;
    const tw = ctx.measureText(text).width;
    const th = 16;
    const labelY = Math.max(0, py - th - 2);
    ctx.globalAlpha = 0.85;
    ctx.fillRect(px, labelY, tw + padX * 2, th + padY);
    ctx.globalAlpha = 1;
    ctx.fillStyle = '#0b0d10';
    ctx.fillText(text, px + padX, labelY + padY);
  });
}

/**
 * Overlay de cajas de objetos detectados (equipamiento).
 * Misma geometría que PoseSkeletonCanvas (object-fit contain + mirror).
 */
export function DetectedObjectsCanvas({
  objectsRef,
  objects,
  mirrorHorizontal = false,
  contentAspect = null,
}: {
  /** Preferido en vivo: lectura imperativa sin setState. */
  objectsRef?: RefObject<DetectedObjectBox[] | null>;
  /** Alternativa controlada (vídeo / snapshot). */
  objects?: DetectedObjectBox[] | null;
  mirrorHorizontal?: boolean;
  contentAspect?: number | null;
}) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    let raf = 0;
    const tick = () => {
      const wrap = wrapRef.current;
      const canvas = canvasRef.current;
      if (wrap && canvas) {
        const list = objectsRef ? objectsRef.current : (objects ?? null);
        drawBoxes(canvas, wrap, list, mirrorHorizontal, contentAspect);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [objectsRef, objects, mirrorHorizontal, contentAspect]);

  return (
    <div
      ref={wrapRef}
      style={{ position: 'absolute', inset: 0, zIndex: 11, pointerEvents: 'none' }}
      aria-hidden
    >
      <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />
    </div>
  );
}
