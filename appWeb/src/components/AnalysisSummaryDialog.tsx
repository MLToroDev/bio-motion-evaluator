import type { AnalysisSummary } from '../lib/videoAnalysisAccumulator';
import { summaryQualityStatus } from '../lib/videoAnalysisAccumulator';
import { MetricTile } from './MetricTile';
import './ui.css';

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

  return (
    <div className="modal-backdrop" role="dialog" aria-modal onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <h2>Resumen del análisis</h2>
        <p className="bm-label-large" style={{ color: 'var(--bm-text-secondary)', marginBottom: 8 }}>
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
            <p style={{ marginTop: 4 }}>
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
        <p className="bm-caption" style={{ marginTop: 12 }}>
          Frames procesados: {summary.framesProcessed} · Con ambas rodillas: {summary.framesWithBothKnees}
        </p>
        <details style={{ marginTop: 12 }}>
          <summary className="bm-label-large" style={{ cursor: 'pointer' }}>
            Detalles por frame
          </summary>
          {summary.minLeftDeg != null && (
            <p className="bm-caption" style={{ marginTop: 8 }}>
              Rodilla I — Mín: {summary.minLeftDeg.toFixed(1)}° (f {summary.minLeftFrame}) · Máx:{' '}
              {summary.maxLeftDeg!.toFixed(1)}° (f {summary.maxLeftFrame})
            </p>
          )}
          {summary.minRightDeg != null && (
            <p className="bm-caption">
              Rodilla D — Mín: {summary.minRightDeg.toFixed(1)}° (f {summary.minRightFrame}) · Máx:{' '}
              {summary.maxRightDeg!.toFixed(1)}° (f {summary.maxRightFrame})
            </p>
          )}
        </details>
        <div className="modal-actions">
          <button
            type="button"
            className="btn-primary"
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--bm-accent)',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
