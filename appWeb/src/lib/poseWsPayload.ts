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

/** Cajas de objetos (equipamiento) del contrato WS v1. */
export type DetectedObjectPayload = {
  label: string;
  label_es?: string;
  confidence: number;
  bbox_norm: [number, number, number, number];
  equipment_slug?: string | null;
};

export function parseDetectedObjects(raw: unknown): DetectedObjectPayload[] {
  if (!Array.isArray(raw)) return [];
  const out: DetectedObjectPayload[] = [];
  for (const item of raw) {
    if (!item || typeof item !== 'object') continue;
    const m = item as Record<string, unknown>;
    const label = typeof m.label === 'string' ? m.label : '';
    if (!label) continue;
    const conf = typeof m.confidence === 'number' ? m.confidence : Number(m.confidence);
    const bb = m.bbox_norm;
    if (!Array.isArray(bb) || bb.length < 4) continue;
    const nums = bb.slice(0, 4).map((v) => (typeof v === 'number' ? v : Number(v)));
    if (nums.some((n) => !Number.isFinite(n))) continue;
    out.push({
      label,
      label_es: typeof m.label_es === 'string' ? m.label_es : undefined,
      confidence: Number.isFinite(conf) ? conf : 0,
      bbox_norm: [nums[0], nums[1], nums[2], nums[3]],
      equipment_slug: typeof m.equipment_slug === 'string' ? m.equipment_slug : null,
    });
  }
  return out;
}

export function pipelineTotalMs(map: Record<string, unknown>): number | null {
  const pm = map.pipeline_ms;
  if (!pm || typeof pm !== 'object' || Array.isArray(pm)) return null;
  const t = (pm as Record<string, unknown>).total;
  if (typeof t === 'number' && Number.isFinite(t)) return Math.round(t);
  return null;
}

/** Veredicto del validador / teacher de ejercicio (extensión WS v1). */
export type ExerciseValidationVerdict = 'confirm' | 'reject' | 'changed' | 'uncertain';

export type ExerciseValidationPayload = {
  verdict: ExerciseValidationVerdict;
  primary_label: string;
  validator_label: string | null;
  confidence: number;
  score_margin: number;
  reason: string;
  previous_label?: string | null;
  teacher_mode?: string;
};

export function parseExerciseValidation(raw: unknown): ExerciseValidationPayload | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const m = raw as Record<string, unknown>;
  const v = typeof m.verdict === 'string' ? m.verdict.trim().toLowerCase() : '';
  if (v !== 'confirm' && v !== 'reject' && v !== 'changed' && v !== 'uncertain') return null;
  const conf = typeof m.confidence === 'number' ? m.confidence : Number(m.confidence);
  const margin = typeof m.score_margin === 'number' ? m.score_margin : Number(m.score_margin);
  return {
    verdict: v,
    primary_label: typeof m.primary_label === 'string' ? m.primary_label : 'unknown',
    validator_label: typeof m.validator_label === 'string' ? m.validator_label : null,
    confidence: Number.isFinite(conf) ? conf : 0,
    score_margin: Number.isFinite(margin) ? margin : 0,
    reason: typeof m.reason === 'string' ? m.reason : '',
    previous_label: typeof m.previous_label === 'string' ? m.previous_label : null,
    teacher_mode: typeof m.teacher_mode === 'string' ? m.teacher_mode : undefined,
  };
}
