import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { BmButton } from '../components/BmButton';
import { DashboardPanel } from '../components/DashboardPanel';
import { PoseSkeletonCanvas } from '../components/PoseSkeletonCanvas';
import { LIVE_POSE_TIPS, VideoPreviewOverlays } from '../components/VideoPreviewOverlays';
import { useLiveAnalysisSession } from '../hooks/useLiveAnalysisSession';
import { kneeFlexionMetricSublabelInContext } from '../lib/angleFormatter';
import { readApiBase, readTargetRepGoal } from '../lib/prefs';
import '../App.css';

export type LiveExerciseMode = 'auto' | 'idle' | 'squat' | 'lunge';

export default function LiveAnalysisPage() {
  const apiBase = useMemo(() => readApiBase(), []);
  const targetRepGoal = useMemo(() => readTargetRepGoal(), []);
  const [exerciseMode, setExerciseMode] = useState<LiveExerciseMode>('auto');
  const forcedLabel = exerciseMode === 'auto' ? null : exerciseMode;
  const { ui, videoRef, startCamera, stopCamera, startTransmit, stopTransmit, statusForLeft, statusForRight } =
    useLiveAnalysisSession(apiBase, false, forcedLabel);

  const ex = ui.exerciseLabel;
  const leftSublabel = kneeFlexionMetricSublabelInContext(ui.leftDeg, true, ex, ui.rightDeg);
  const rightSublabel = kneeFlexionMetricSublabelInContext(ui.rightDeg, false, ex, ui.leftDeg);

  return (
    <div className="app">
      <header className="header">
        <h1 className="bm-screen-title">Análisis en vivo</h1>
        <p className="subtitle">
          Cámara + WebSocket <code>/ws/video</code> (JPEG binario). Usa <code>https</code> o{' '}
          <code>localhost</code> para permisos de cámara.
        </p>
      </header>

      {ui.error && <p className="error">{ui.error}</p>}

      <div className="layout" style={{ gridTemplateColumns: '1fr' }}>
        <main className="main" style={{ maxWidth: 960 }}>
          <p className="bm-caption bm-mono" style={{ marginBottom: 'var(--bm-space-md)' }}>
            RTT: {ui.serverRttMs != null ? `${ui.serverRttMs} ms` : '—'} · RX/s: {ui.displayRxPerSec} · Frame:{' '}
            {ui.frameIndex >= 0 ? ui.frameIndex : '—'}
          </p>

          <div
            className="preview-stack"
            style={{
              aspectRatio: '4/3',
              maxHeight: 420,
              marginBottom: 'var(--bm-space-md)',
              borderColor: ui.transmitting ? 'var(--bm-accent)' : undefined,
              boxShadow: ui.transmitting ? '0 0 0 1px var(--bm-accent-muted)' : undefined,
            }}
          >
            <video
              ref={videoRef}
              playsInline
              muted
              autoPlay
              style={{
                position: 'absolute',
                inset: 0,
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                display: ui.cameraOn ? 'block' : 'none',
              }}
            />
            {ui.transmitting && <PoseSkeletonCanvas landmarks={ui.landmarks} mirrorHorizontal={true} />}
            <VideoPreviewOverlays
              visible={ui.cameraOn}
              hudSections={{ exercise: ui.transmitting }}
              modeLabel="WEB"
              rxPerSec={ui.transmitting ? ui.displayRxPerSec : 0}
              rateSuffix="RX/s"
              bullets={LIVE_POSE_TIPS}
              qualityFlags={ui.transmitting ? ui.qualityFlags : []}
              exerciseLabel={ex}
              exerciseConfidence={ui.exerciseConfidence}
            />
            {!ui.cameraOn && (
              <div
                className="bm-empty-state"
                style={{
                  position: 'absolute',
                  inset: 0,
                  background: 'var(--bm-background)',
                  minHeight: 'unset',
                }}
              >
                <p className="bm-body" style={{ textAlign: 'center', color: 'var(--bm-text-secondary)' }}>
                  Posiciónate a 2–3 metros de la cámara,
                  <br />
                  de cuerpo entero, y pulsa Iniciar.
                </p>
                <BmButton variant="primary" onClick={() => void startCamera()}>
                  Conectar cámara
                </BmButton>
              </div>
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--bm-space-sm)', marginBottom: 'var(--bm-space-md)' }}>
            <label className="bm-caption" style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
              <span style={{ color: 'var(--bm-text-secondary)' }}>Ejercicio (clasificador)</span>
              <select
                value={exerciseMode}
                onChange={(e) => setExerciseMode(e.target.value as LiveExerciseMode)}
                disabled={ui.transmitting}
                style={{
                  maxWidth: 280,
                  padding: '0.45rem 0.6rem',
                  borderRadius: 'var(--bm-radius-sm)',
                  border: '1px solid var(--bm-border)',
                  background: 'var(--bm-surface)',
                  color: 'var(--bm-text-primary)',
                  fontFamily: 'var(--bm-font-body)',
                }}
              >
                <option value="auto">Automático</option>
                <option value="idle">idle</option>
                <option value="squat">squat</option>
                <option value="lunge">lunge</option>
              </select>
              {ui.transmitting ? (
                <span style={{ color: 'var(--bm-text-disabled)', fontSize: '0.75rem' }}>
                  Detén la transmisión para cambiar el modo.
                </span>
              ) : (
                <span style={{ color: 'var(--bm-text-disabled)', fontSize: '0.75rem' }}>
                  «Automático» usa el motor del servidor; otras opciones fijan la etiqueta (confianza 1,0).
                </span>
              )}
            </label>
            {ui.cameraOn && ui.transmitting && (
              <BmButton variant="outline" onClick={stopTransmit} style={{ width: '100%', fontWeight: 700, letterSpacing: '0.06em' }}>
                DETENER
              </BmButton>
            )}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--bm-space-sm)' }}>
              {ui.cameraOn && (
                <>
                  <BmButton variant="outline" onClick={stopCamera} disabled={ui.transmitting}>
                    Apagar cámara
                  </BmButton>
                  {!ui.transmitting ? (
                    <BmButton variant="primary" onClick={() => void startTransmit()} style={{ flex: '1 1 160px' }}>
                      Iniciar transmisión
                    </BmButton>
                  ) : null}
                </>
              )}
            </div>
          </div>

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

          <p className="bm-caption" style={{ marginTop: 'var(--bm-space-lg)' }}>
            <Link to="/settings/connection" style={{ color: 'var(--bm-accent)' }}>
              Configuración de conexión
            </Link>
          </p>
        </main>
      </div>
    </div>
  );
}
