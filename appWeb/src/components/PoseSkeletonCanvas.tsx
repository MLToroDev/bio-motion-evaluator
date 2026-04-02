import { useEffect, useRef } from 'react';
import { POSE_CONNECTIONS } from '../lib/poseTopology';
import type { LandmarkMap } from '../lib/poseWsPayload';

const MIN_VIS = 0.4;

function cssVar(name: string, fallback: string): string {
  if (typeof document === 'undefined') return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
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

function landmarkPoint(
  lm: LandmarkMap,
  w: number,
  h: number,
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
  return { x: nx * w, y: y * h };
}

export function PoseSkeletonCanvas({
  landmarks,
  mirrorHorizontal = false,
}: {
  landmarks: LandmarkMap[] | null;
  mirrorHorizontal?: boolean;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const wrap = wrapRef.current;
    if (!canvas || !wrap) return;

    const draw = () => {
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

      const lm = landmarks;
      const mirror = mirrorHorizontal;
      if (!lm || lm.length === 0) return;

      const points = new Map<number, { x: number; y: number }>();
      for (const m of lm) {
        const i = m.index;
        if (typeof i !== 'number') continue;
        const p = landmarkPoint(m, cw, ch, mirror);
        if (p) points.set(i, p);
      }

      const lineRgb = cssVar('--bm-skeleton-line', '#00e676');
      ctx.strokeStyle = lineRgb.startsWith('#') ? hexToRgba(lineRgb, 0.85) : lineRgb;
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

      ctx.fillStyle = cssVar('--bm-skeleton-joint', '#ffffff');
      ctx.strokeStyle = hexToRgba(cssVar('--bm-skeleton-joint-border', '#00e676'), 0.35);
      for (const p of points.values()) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, 3.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      }
    };

    draw();
    const ro = new ResizeObserver(() => draw());
    ro.observe(wrap);
    return () => ro.disconnect();
  }, [landmarks, mirrorHorizontal]);

  return (
    <div ref={wrapRef} className="pose-canvas-wrap">
      <canvas ref={canvasRef} className="pose-canvas" aria-hidden />
    </div>
  );
}
