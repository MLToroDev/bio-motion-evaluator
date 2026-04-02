import type { MetricStatus } from './metricStatus';

/** Port de angle_ranges.dart */
export const squatFlexGoodMinDeg = 80;
export const squatFlexGoodMaxDeg = 100;
export const squatFlexAdjustShallowMaxDeg = 79;
export const squatFlexAdjustShallowMinDeg = 60;
export const squatFlexAdjustDeepMinDeg = 101;
export const squatFlexAdjustDeepMaxDeg = 120;

export function kneeFlexionStatus(deg: number): MetricStatus {
  if (deg >= squatFlexGoodMinDeg && deg <= squatFlexGoodMaxDeg) return 'good';
  if (
    (deg >= squatFlexAdjustShallowMinDeg && deg <= squatFlexAdjustShallowMaxDeg) ||
    (deg >= squatFlexAdjustDeepMinDeg && deg <= squatFlexAdjustDeepMaxDeg)
  ) {
    return 'warn';
  }
  return 'bad';
}

export function lungeFrontKneeFlexionStatus(deg: number): MetricStatus {
  if (deg >= 50 && deg <= 90) return 'good';
  if ((deg >= 40 && deg < 50) || (deg > 90 && deg <= 100)) return 'warn';
  return 'bad';
}

export function lungeRearKneeFlexionStatus(deg: number): MetricStatus {
  if (deg >= 0 && deg <= 45) return 'good';
  if (deg > 45 && deg <= 65) return 'warn';
  return 'bad';
}

export function isLungeExerciseLabel(label: string): boolean {
  const n = label.toLowerCase().trim();
  if (!n || n === 'unknown') return false;
  return n.includes('lunge') || n.includes('zancada');
}

export function isSquatLikeExerciseLabel(label: string): boolean {
  const n = label.toLowerCase().trim();
  if (!n || n === 'unknown') return false;
  return n.includes('squat') || n.includes('sentadilla');
}

export function isRunningLikeExerciseLabel(label: string): boolean {
  const n = label.toLowerCase().trim();
  if (!n || n === 'unknown') return false;
  return n.includes('run') || n.includes('carrera') || n.includes('jog') || n.includes('running');
}

export function shouldShowSquatKneeRomGuideBands(exerciseLabel: string): boolean {
  return isSquatLikeExerciseLabel(exerciseLabel);
}

export function kneeFlexionStatusForExercise(
  deg: number,
  isLeftLeg: boolean,
  exerciseLabel: string,
  otherLegDeg: number | null | undefined,
  minFlexDeltaDeg = 5,
): MetricStatus {
  if (isLungeExerciseLabel(exerciseLabel)) {
    const o = otherLegDeg;
    if (o == null || Number.isNaN(deg) || Number.isNaN(o)) return 'neutral';
    if (Math.abs(deg - o) < minFlexDeltaDeg) return 'neutral';
    const thisIsFront = isLeftLeg ? deg >= o : deg > o;
    return thisIsFront ? lungeFrontKneeFlexionStatus(deg) : lungeRearKneeFlexionStatus(deg);
  }
  if (isSquatLikeExerciseLabel(exerciseLabel)) {
    return kneeFlexionStatus(deg);
  }
  return 'neutral';
}
