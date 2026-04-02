import type { AnalysisSummary } from '../lib/videoAnalysisAccumulator';
import { summaryQualityStatus } from '../lib/videoAnalysisAccumulator';
import { MetricTile } from './MetricTile';
import './ui.css';

function peakHighlight(s: AnalysisSummary): { label: string; value: string } {
  const ml = s.maxLeftDeg;
  const mr = s.maxRightDeg;
  if (ml == null && mr == null) return { label: 'Pico ROM', value: '—' };
  if (mr == null || (ml != null && ml >= mr)) {
    return { label: 'Pico rodilla izq.', value: `${ml!.toFixed(1)}°` };
  }
  return { label: 'Pico rodilla der.', value: `${mr!.toFixed(1)}°` };
}

function motivationalLine(s: AnalysisSummary): string {
  const ml = s.meanLeftDeg;
  const mr = s.meanRightDeg;
  if (ml != null && mr != null) {
    const diff = Math.abs(ml - mr);
    if (diff < 5) return 'Buena simetría entre ambas rodillas.';
    if (mr > ml) return 'Buena movilidad de rodilla derecha. Trabaja el rango izquierdo.';
    return 'Buena movilidad de rodilla izquierda. Trabaja el rango derecho.';
  }
  if (mr != null && ml == null) return 'Datos destacados en rodilla derecha.';
  if (ml != null && mr == null) return 'Datos destacados en rodilla izquierda.';
  return 'Sigue registrando sesiones para comparar ambos lados.';
}

export function AnalysisSummaryDialog({
  summary,
  open,
  onClose,
}: {
  summary: AnalysisSummary | null;
  open: boolean;
  onClose: () => void;
}) {
  if (!open || !summary) return null;
  const qs = summaryQualityStatus(summary);
  const romSublabel =
    qs === 'good'
      ? 'Excelente movilidad en este movimiento'
      : qs === 'warn'
        ? 'Movilidad en zona de mejora'
        : qs === 'bad'
          ? 'Requiere trabajo de movilidad específico'
          : null;
  const peak = peakHighlight(summary);

  return (
    <div className="modal-backdrop" role="dialog" aria-modal onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <button
          type="button"
          className="modal-close-x"
          onClick={onClose}
          aria-label="Cerrar"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
        <h2 className="modal-dialog__title">Resumen del análisis</h2>
        <p className="bm-label-large" style={{ color: 'var(--bm-text-secondary)', marginBottom: 8 }}>
          Mejor ángulo logrado
        </p>
        <MetricTile label={peak.label} value={peak.value} status="good" />
        <p className="bm-body" style={{ marginTop: 12, color: 'var(--bm-text-secondary)' }}>
          {motivationalLine(summary)}
        </p>
        <p className="bm-label-large" style={{ color: 'var(--bm-text-secondary)', marginTop: 16, marginBottom: 8 }}>
          Zona principal (calidad ROM)
        </p>
        <MetricTile
          label="Calidad ROM bilateral"
          value={`${summary.pctGood.toFixed(1)} %`}
          sublabel={romSublabel}
          status={qs}
        />
        {(summary.lastRepCount > 0 ||
          summary.lastExerciseLabel !== 'unknown' ||
          summary.lastQualityFlags.length > 0) && (
          <div style={{ marginTop: 16 }}>
            <p className="bm-label-large" style={{ color: 'var(--bm-text-secondary)' }}>
              Motor (último frame)
            </p>
            <p className="bm-body" style={{ marginTop: 4 }}>
              {summary.lastExerciseLabel.toUpperCase()} · reps {summary.lastRepCount} · fase {summary.lastRepPhase}
            </p>
            {summary.lastQualityFlags.length > 0 && (
              <p className="bm-caption" style={{ color: 'var(--bm-angle-warn)', marginTop: 4 }}>
                Alertas: {summary.lastQualityFlags.join(', ')}
              </p>
            )}
          </div>
        )}
        <p className="bm-label-large" style={{ color: 'var(--bm-text-secondary)', marginTop: 16 }}>
          Medias por lado
        </p>
        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <MetricTile
            label="Media izq."
            value={summary.meanLeftDeg != null ? `${summary.meanLeftDeg.toFixed(1)}°` : '—'}
            status="neutral"
            compact
          />
          <MetricTile
            label="Media der."
            value={summary.meanRightDeg != null ? `${summary.meanRightDeg.toFixed(1)}°` : '—'}
            status="neutral"
            compact
          />
        </div>
        <p className="bm-caption bm-mono" style={{ marginTop: 12 }}>
          Frames procesados: {summary.framesProcessed} · Con ambas rodillas: {summary.framesWithBothKnees}
        </p>
        <details style={{ marginTop: 12 }}>
          <summary className="bm-label-large" style={{ cursor: 'pointer', color: 'var(--bm-text-secondary)' }}>
            Detalles por frame
          </summary>
          {summary.minLeftDeg != null && (
            <p className="bm-caption bm-mono" style={{ marginTop: 8 }}>
              Rodilla I — Mín: {summary.minLeftDeg.toFixed(1)}° (f {summary.minLeftFrame}) · Máx:{' '}
              {summary.maxLeftDeg!.toFixed(1)}° (f {summary.maxLeftFrame})
            </p>
          )}
          {summary.minRightDeg != null && (
            <p className="bm-caption bm-mono">
              Rodilla D — Mín: {summary.minRightDeg.toFixed(1)}° (f {summary.minRightFrame}) · Máx:{' '}
              {summary.maxRightDeg!.toFixed(1)}° (f {summary.maxRightFrame})
            </p>
          )}
        </details>
      </div>
    </div>
  );
}
