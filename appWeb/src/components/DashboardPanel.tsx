import { useState } from 'react';
import type { FrameLogEntry } from '../lib/frameLogEntry';
import { AngleHistoryChart } from './AngleHistoryChart';
import { FrameLogPanel } from './FrameLogPanel';
import { MetricTile } from './MetricTile';
import { ProgressRing } from './ProgressRing';
import './ui.css';
import type { MetricStatus } from '../lib/metricStatus';

type Tab = 'metrics' | 'log' | 'history';

export function DashboardPanel({
  running,
  captureOnly,
  targetRepGoal,
  exerciseLabel,
  exerciseConfidence,
  repPhase,
  repCount,
  leftDeg,
  rightDeg,
  leftStatus,
  rightStatus,
  leftSublabel,
  rightSublabel,
  displayRxPerSec,
  logEntries,
  leftSeries,
  rightSeries,
  className = '',
}: {
  running: boolean;
  captureOnly: boolean;
  targetRepGoal: number | null;
  exerciseLabel: string;
  exerciseConfidence: number;
  repPhase: string;
  repCount: number;
  leftDeg: number | null;
  rightDeg: number | null;
  leftStatus: MetricStatus;
  rightStatus: MetricStatus;
  leftSublabel: string;
  rightSublabel: string;
  displayRxPerSec: number;
  logEntries: FrameLogEntry[];
  leftSeries: number[];
  rightSeries: number[];
  className?: string;
}) {
  const [tab, setTab] = useState<Tab>('metrics');
  const repProgress =
    targetRepGoal != null && targetRepGoal > 0 ? Math.min(1, repCount / targetRepGoal) : null;

  return (
    <div className={`dashboard-panel ${className}`.trim()}>
      <div className="dashboard-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'metrics'}
          className={`dashboard-tab ${tab === 'metrics' ? 'dashboard-tab--active' : ''}`}
          onClick={() => setTab('metrics')}
        >
          Métricas
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'log'}
          className={`dashboard-tab ${tab === 'log' ? 'dashboard-tab--active' : ''}`}
          onClick={() => setTab('log')}
        >
          Log
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'history'}
          className={`dashboard-tab ${tab === 'history' ? 'dashboard-tab--active' : ''}`}
          onClick={() => setTab('history')}
        >
          Historial
        </button>
      </div>
      <div className="dashboard-body">
        {tab === 'metrics' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <p className="bm-caption">Mensajes/s (UI): {displayRxPerSec}</p>
            {running && !captureOnly && (
              <>
                <MetricTile
                  label="Ejercicio"
                  value={exerciseLabel.toUpperCase()}
                  sublabel={`Confianza ${Math.min(100, Math.max(0, exerciseConfidence * 100)).toFixed(0)}%`}
                  status="neutral"
                />
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <MetricTile
                    label="Fase / reps"
                    value={repPhase}
                    sublabel={
                      targetRepGoal != null && targetRepGoal > 0
                        ? `Cuenta: ${repCount} / ${targetRepGoal}`
                        : `Cuenta: ${repCount}`
                    }
                    status="neutral"
                  />
                  {repProgress != null && <ProgressRing progress={repProgress} />}
                </div>
              </>
            )}
            {leftDeg != null && (
              <MetricTile
                label="Rodilla izq."
                value={`${leftDeg.toFixed(1)}°`}
                sublabel={leftSublabel}
                status={leftStatus}
              />
            )}
            {rightDeg != null && (
              <MetricTile
                label="Rodilla der."
                value={`${rightDeg.toFixed(1)}°`}
                sublabel={rightSublabel}
                status={rightStatus}
              />
            )}
            {leftDeg == null && rightDeg == null && (
              <p className="bm-caption">Esperando datos de rodillas del servidor…</p>
            )}
          </div>
        )}
        {tab === 'log' && <FrameLogPanel entries={logEntries} />}
        {tab === 'history' && <AngleHistoryChart leftSeries={leftSeries} rightSeries={rightSeries} />}
      </div>
    </div>
  );
}
