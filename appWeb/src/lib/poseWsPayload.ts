export type LandmarkMap = Record<string, unknown>;

export function poseWsErrorMessage(map: Record<string, unknown>): string | null {
  if (!('error' in map)) return null;
  const e = String(map.error);
  if (e === 'sin_frame') return null;
  return e;
}

export function parseLandmarksJson(raw: unknown): LandmarkMap[] | null {
  if (!Array.isArray(raw) || raw.length === 0) return null;
  try {
    return raw.map((e) => {
      if (e && typeof e === 'object') return { ...(e as object) } as LandmarkMap;
      throw new Error('bad landmark');
    });
  } catch {
    return null;
  }
}

export function parseKneesMap(raw: unknown): Record<string, unknown> | null {
  if (raw && typeof raw === 'object' && !Array.isArray(raw)) {
    return { ...(raw as object) };
  }
  return null;
}

export function parseDeg(v: unknown): number | null {
  if (v == null) return null;
  const n = typeof v === 'number' ? v : Number(v);
  if (Number.isNaN(n)) return null;
  return n;
}

export function parseFrameIndex(raw: unknown): number {
  if (typeof raw === 'number' && Number.isFinite(raw)) return Math.trunc(raw);
  return -1;
}

export function parseTotalFrames(raw: unknown): number | null {
  if (raw == null) return null;
  const n = typeof raw === 'number' ? raw : Number(raw);
  if (!Number.isFinite(n)) return null;
  const t = Math.trunc(n);
  return t > 0 ? t : null;
}

export function parseQualityFlags(raw: unknown): string[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((e) => String(e));
}

export function pipelineTotalMs(map: Record<string, unknown>): number | null {
  const pm = map.pipeline_ms;
  if (!pm || typeof pm !== 'object' || Array.isArray(pm)) return null;
  const t = (pm as Record<string, unknown>).total;
  if (typeof t === 'number' && Number.isFinite(t)) return Math.round(t);
  return null;
}
