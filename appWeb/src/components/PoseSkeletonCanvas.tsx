import { useEffect, useRef } from 'react';
import { POSE_CONNECTIONS } from '../lib/poseTopology';
import type { LandmarkMap } from '../lib/poseWsPayload';

const MIN_VIS = 0.4;

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

      ctx.strokeStyle = 'rgba(0, 230, 180, 0.85)';
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

      ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
      ctx.strokeStyle = 'rgba(0, 0, 0, 0.35)';
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
