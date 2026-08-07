import type { LandmarkMap } from './poseWsPayload';

function lerpNum(a: unknown, b: unknown, t: number): number | undefined {
  const na = typeof a === 'number' ? a : Number(a);
  const nb = typeof b === 'number' ? b : Number(b);
  if (Number.isNaN(na) || Number.isNaN(nb)) return typeof b === 'number' ? b : undefined;
  return na + (nb - na) * t;
}

/** Interpola landmarks por `index` entre dos poses (t ∈ [0, 1]) en un buffer reutilizable. */
export function lerpLandmarksInto(
  from: LandmarkMap[] | null,
  to: LandmarkMap[] | null,
  t: number,
  out: LandmarkMap[],
): void {
  if (!to || to.length === 0) {
    out.length = 0;
    return;
  }
  const clamped = Math.max(0, Math.min(1, t));
  if (!from || from.length === 0 || clamped >= 1) {
    out.length = to.length;
    for (let i = 0; i < to.length; i++) {
      if (!out[i]) out[i] = { ...to[i] };
      else Object.assign(out[i], to[i]);
    }
    return;
  }

  const fromByIndex = new Map<number, LandmarkMap>();
  for (const m of from) {
    const idx = m.index;
    if (typeof idx === 'number') fromByIndex.set(idx, m);
  }

  out.length = to.length;
  for (let i = 0; i < to.length; i++) {
    const tgt = to[i];
    const idx = tgt.index;
    if (typeof idx !== 'number') {
      if (!out[i]) out[i] = { ...tgt };
      else Object.assign(out[i], tgt);
      continue;
    }
    const src = fromByIndex.get(idx);
    if (!src) {
      if (!out[i]) out[i] = { ...tgt };
      else Object.assign(out[i], tgt);
      continue;
    }
    if (!out[i]) out[i] = { ...tgt };
    const slot = out[i];
    const x = lerpNum(src.x, tgt.x, clamped);
    const y = lerpNum(src.y, tgt.y, clamped);
    const z = lerpNum(src.z, tgt.z, clamped);
    const vis = lerpNum(src.visibility, tgt.visibility, clamped);
    slot.index = idx;
    if (x != null) slot.x = x;
    if (y != null) slot.y = y;
    if (z != null) slot.z = z;
    if (vis != null) slot.visibility = vis;
  }
}

/** Interpola landmarks por `index` entre dos poses (t ∈ [0, 1]). */
export function lerpLandmarks(
  from: LandmarkMap[] | null,
  to: LandmarkMap[] | null,
  t: number,
): LandmarkMap[] | null {
  if (!to || to.length === 0) return null;
  const out: LandmarkMap[] = [];
  lerpLandmarksInto(from, to, t, out);
  return out.length > 0 ? out : null;
}
