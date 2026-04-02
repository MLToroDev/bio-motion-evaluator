import {
  isLungeExerciseLabel,
  isRunningLikeExerciseLabel,
  isSquatLikeExerciseLabel,
  kneeFlexionStatus,
  kneeFlexionStatusForExercise,
  squatFlexAdjustDeepMaxDeg,
  squatFlexGoodMaxDeg,
  squatFlexGoodMinDeg,
} from './angleRanges';
import type { MetricStatus } from './metricStatus';

export function formatDeg(v: unknown): string {
  if (v == null) return '—';
  const n = typeof v === 'number' ? v : Number(v);
  if (Number.isNaN(n)) return '—';
  return `${n.toFixed(1)}°`;
}

export function parseDeg(v: unknown): number | null {
  if (v == null) return null;
  const n = typeof v === 'number' ? v : Number(v);
  if (Number.isNaN(n)) return null;
  return n;
}

export function statusForKneeFlexionInContext(
  deg: number,
  isLeftLeg: boolean,
  exerciseLabel: string,
  otherLegDeg: number | null | undefined,
): MetricStatus {
  return kneeFlexionStatusForExercise(deg, isLeftLeg, exerciseLabel, otherLegDeg);
}

function lungeFrontRomProgress(deg: number): number {
  const lo = 50;
  const hi = 90;
  if (deg >= lo && deg <= hi) return 1;
  if (deg < lo) return Math.min(1, Math.max(0, deg / lo));
  return Math.min(1, Math.max(0, (100 - deg) / (100 - hi)));
}

function lungeRearRomProgress(deg: number): number {
  const hi = 35;
  if (deg >= 0 && deg <= hi) return 1;
  if (deg > hi) return Math.min(1, Math.max(0, (65 - deg) / (65 - hi)));
  return 0;
}

export function kneeFlexionRomProgress(deg: number): number {
  const lo = squatFlexGoodMinDeg;
  const hi = squatFlexGoodMaxDeg;
  if (deg >= lo && deg <= hi) return 1;
  if (deg < lo) return Math.min(1, Math.max(0, deg / lo));
  const dMax = squatFlexAdjustDeepMaxDeg;
  return Math.min(1, Math.max(0, (dMax - deg) / (dMax - hi)));
}

export function kneeFlexionRomProgressInContext(
  deg: number,
  isLeftLeg: boolean,
  exerciseLabel: string,
  otherLegDeg: number | null | undefined,
): number {
  if (isLungeExerciseLabel(exerciseLabel)) {
    const o = otherLegDeg;
    if (o == null || Number.isNaN(deg) || Number.isNaN(o)) return 0.5;
    if (Math.abs(deg - o) < 5) return 0.5;
    const front = isLeftLeg ? deg >= o : deg > o;
    return front ? lungeFrontRomProgress(deg) : lungeRearRomProgress(deg);
  }
  if (isSquatLikeExerciseLabel(exerciseLabel)) {
    return kneeFlexionRomProgress(deg);
  }
  return 0.5;
}

export function kneeFlexionMetricSublabel(deg: number | null): string {
  if (deg == null) return 'Sin datos';
  const st = kneeFlexionStatus(deg);
  if (st === 'good') return 'Rango óptimo (80–100°) ✓';
  if (st === 'warn') {
    if (deg < squatFlexGoodMinDeg) return 'Ajusta: poca profundidad';
    return 'Ajusta: mucha profundidad';
  }
  return 'Fuera de rango seguro';
}

export function kneeFlexionMetricSublabelInContext(
  deg: number | null,
  isLeftLeg: boolean,
  exerciseLabel: string,
  otherLegDeg: number | null | undefined,
): string {
  if (deg == null) return 'Sin datos';
  if (isSquatLikeExerciseLabel(exerciseLabel)) {
    return kneeFlexionMetricSublabel(deg);
  }
  if (!isLungeExerciseLabel(exerciseLabel)) {
    if (isRunningLikeExerciseLabel(exerciseLabel)) {
      return 'Carrera: ángulo referencial (no aplica sentadilla)';
    }
    const n = exerciseLabel.toLowerCase().trim();
    if (!n || n === 'unknown') return 'Sin clasificar: ángulo referencial';
    return `Ángulo referencial (${exerciseLabel.toUpperCase()})`;
  }
  const o = otherLegDeg;
  if (o == null || Number.isNaN(deg) || Number.isNaN(o)) {
    return 'Zancada: faltan ambas rodillas para evaluar';
  }
  if (Math.abs(deg - o) < 5) {
    return 'Zancada: flexión similar en ambas — revisa encuadre';
  }
  const front = isLeftLeg ? deg >= o : deg > o;
  const role = front ? 'Delantera' : 'Trasera';
  const st = kneeFlexionStatusForExercise(deg, isLeftLeg, exerciseLabel, o);
  if (st === 'good') {
    return front ? `Zancada — ${role}: 50–90° ✓` : `Zancada — ${role}: extensión OK ✓`;
  }
  if (st === 'warn') {
    return front ? `Zancada — ${role}: ajusta flexión (50–90°)` : `Zancada — ${role}: extiende más la rodilla`;
  }
  return `Zancada — ${role}: fuera de rango`;
}
