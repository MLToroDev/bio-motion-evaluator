/** Equivalente a `MetricStatus` en metric_tile.dart */
export type MetricStatus = 'good' | 'warn' | 'bad' | 'neutral';

export function worstRom(a: MetricStatus, b: MetricStatus): MetricStatus {
  if (a === 'bad' || b === 'bad') return 'bad';
  if (a === 'warn' || b === 'warn') return 'warn';
  if (a === 'good' && b === 'good') return 'good';
  return 'neutral';
}
