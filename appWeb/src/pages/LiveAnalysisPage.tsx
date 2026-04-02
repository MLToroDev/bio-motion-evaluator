import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { DashboardPanel } from '../components/DashboardPanel';
import { PoseSkeletonCanvas } from '../components/PoseSkeletonCanvas';
import { useLiveAnalysisSession } from '../hooks/useLiveAnalysisSession';
import { kneeFlexionMetricSublabelInContext } from '../lib/angleFormatter';
import { readApiBase, readTargetRepGoal } from '../lib/prefs';
import '../App.css';

export default function LiveAnalysisPage() {
  const apiBase = useMemo(() => readApiBase(), []);
  const targetRepGoal = useMemo(() => readTargetRepGoal(), []);
  const { ui, videoRef, startCamera, stopCamera, startTransmit, stopTransmit, statusForLeft, statusForRight } =
    useLiveAnalysisSession(apiBase, false);

  const ex = ui.exerciseLabel;
  const leftSublabel = kneeFlexionMetricSublabelInContext(ui.leftDeg, true, ex, ui.rightDeg);
  const rightSublabel = kneeFlexionMetricSublabelInContext(ui.rightDeg, false, ex, ui.leftDeg);

  return (
    <div className="app">
      <header className="header">
        <h1>Análisis en vivo</h1>
        <p className="subtitle">
          Cámara + WebSocket <code>/ws/video</code> (JPEG binario). Usa <code>https</code> o{' '}
          <code>localhost</code> para permisos de cámara.
        </p>
        <p className="bm-caption">
          <Link to="/settings/connection" style={{ color: 'var(--bm-accent)' }}>
            Configuración de conexión
          </Link>
        </p>
      </header>

      {ui.error && <p className="error" style={{ marginBottom: 12 }}>{ui.error}</p>}

      <div className="layout" style={{ gridTemplateColumns: '1fr' }}>
        <main className="main" style={{ maxWidth: 960 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
            {!ui.cameraOn ? (
              <button type="button" className="primary" onClick={() => void startCamera()}>
                Conectar cámara
              </button>
            ) : (
              <>
                <button type="button" onClick={stopCamera} disabled={ui.transmitting}>
                  Apagar cámara
                </button>
                {!ui.transmitting ? (
                  <button type="button" className="primary" onClick={() => void startTransmit()}>
                    Iniciar transmisión
                  </button>
                ) : (
                  <button type="button" onClick={stopTransmit}>
                    Detener transmisión
                  </button>
                )}
              </>
            )}
          </div>

          <div
            className="preview-stack"
            style={{ aspectRatio: '4/3', maxHeight: 420, marginBottom: 16 }}
          >
            <video
              ref={videoRef}
              playsInline
              muted
              autoPlay
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                display: ui.cameraOn ? 'block' : 'none',
              }}
            />
            {ui.transmitting && (
              <PoseSkeletonCanvas landmarks={ui.landmarks} mirrorHorizontal={true} />
            )}
            {!ui.cameraOn && (
              <div className="preview-placeholder">Conecta la cámara para ver la vista previa</div>
            )}
          </div>

          <p className="bm-caption bm-mono" style={{ marginBottom: 12 }}>
            RTT: {ui.serverRttMs != null ? `${ui.serverRttMs} ms` : '—'} · RX/s: {ui.displayRxPerSec} · Frame:{' '}
            {ui.frameIndex >= 0 ? ui.frameIndex : '—'}
          </p>

          <DashboardPanel
            running={ui.transmitting}
            captureOnly={false}
            targetRepGoal={targetRepGoal}
            exerciseLabel={ex}
            exerciseConfidence={ui.exerciseConfidence}
            repPhase={ui.repPhase}
            repCount={ui.repCount}
            leftDeg={ui.leftDeg}
            rightDeg={ui.rightDeg}
            leftStatus={statusForLeft(ex)}
            rightStatus={statusForRight(ex)}
            leftSublabel={leftSublabel}
            rightSublabel={rightSublabel}
            displayRxPerSec={ui.displayRxPerSec}
            logEntries={[]}
            leftSeries={ui.leftSeries}
            rightSeries={ui.rightSeries}
          />
        </main>
      </div>
    </div>
  );
}
