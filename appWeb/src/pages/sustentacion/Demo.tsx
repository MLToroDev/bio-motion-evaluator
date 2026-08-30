import { useMemo } from 'react';
import { PoseSkeletonCanvas } from '../../components/PoseSkeletonCanvas';
import { useLiveAnalysisSession } from '../../hooks/useLiveAnalysisSession';
import type { MetricStatus } from '../../lib/metricStatus';
import { readApiBase } from '../../lib/prefs';

/** Traduce el estado de la métrica a la clase de color del tema claro. */
function claseEstado(estado: MetricStatus): string {
  if (estado === 'good') return ' sus-angle--good';
  if (estado === 'warn') return ' sus-angle--warn';
  if (estado === 'bad') return ' sus-angle--bad';
  return '';
}

function formatearGrados(deg: number | null): string {
  return deg == null ? '—' : `${deg.toFixed(1)}°`;
}

export default function Demo() {
  const apiBase = useMemo(() => readApiBase(), []);
  const {
    ui,
    overlayLandmarksRef,
    videoRef,
    videoContentAspect,
    startCamera,
    stopCamera,
    startTransmit,
    stopTransmit,
    statusForLeft,
    statusForRight,
  } = useLiveAnalysisSession(apiBase, false, null);

  const ejercicio = ui.exerciseLabel;
  const asimetria =
    ui.leftDeg != null && ui.rightDeg != null ? Math.abs(ui.leftDeg - ui.rightDeg) : null;

  // El piso de ruido medido del estimador es ~5° (§ 7.2.4 de la memoria):
  // por debajo de esa cota la asimetría no es distinguible del ruido.
  const asimetriaInterpretable = asimetria != null && asimetria >= 5;

  return (
    <main className="sus__main sus__main--wide">
      <p className="sus-eyebrow">Demostración en vivo</p>
      <h1 className="sus-h1" style={{ fontSize: 'clamp(1.5rem, 2.6vw, 2rem)' }}>
        Medición angular en tiempo real
      </h1>
      <p className="sus-lead">
        La cámara captura, el servidor infiere la pose y devuelve el ángulo. Colócate de cuerpo
        entero, a 2–3 metros y de perfil respecto a la cámara.
      </p>

      {ui.error && <p className="sus-error">{ui.error}</p>}

      <div className="sus-demo" style={{ marginTop: '1.75rem' }}>
        <div>
          <div className={`sus-stage${ui.transmitting ? ' sus-stage--live' : ''}`}>
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
                objectFit: 'contain',
                transform: 'scaleX(-1)',
                display: ui.cameraOn ? 'block' : 'none',
              }}
            />
            {ui.transmitting && (
              <PoseSkeletonCanvas
                landmarksRef={overlayLandmarksRef}
                mirrorHorizontal
                contentAspect={videoContentAspect}
                smoothMotion
              />
            )}
            {!ui.cameraOn && (
              <div className="sus-stage__idle">
                <p>
                  Sitúate a 2–3 metros de la cámara, de cuerpo entero y con las piernas visibles.
                </p>
                <button type="button" className="sus-btn sus-btn--primary" onClick={() => void startCamera()}>
                  Conectar cámara
                </button>
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: '0.7rem', flexWrap: 'wrap', marginTop: '1rem' }}>
            {ui.cameraOn && !ui.transmitting && (
              <button
                type="button"
                className="sus-btn sus-btn--primary"
                style={{ flex: '1 1 200px' }}
                onClick={() => void startTransmit()}
              >
                Iniciar medición
              </button>
            )}
            {ui.transmitting && (
              <button
                type="button"
                className="sus-btn sus-btn--outline"
                style={{ flex: '1 1 200px' }}
                onClick={stopTransmit}
              >
                Detener medición
              </button>
            )}
            {ui.cameraOn && (
              <button
                type="button"
                className="sus-btn sus-btn--outline"
                onClick={stopCamera}
                disabled={ui.transmitting}
              >
                Apagar cámara
              </button>
            )}
          </div>

          {ui.transmitting && (
            <p className="sus-telemetry">
              <span>RX/s {ui.displayRxPerSec}</span>
              <span>RTT {ui.serverRttMs != null ? `${ui.serverRttMs} ms` : '—'}</span>
              <span>
                Motor {ui.serverPipelineTotalMs != null ? `${ui.serverPipelineTotalMs.toFixed(1)} ms` : '—'}
              </span>
              <span>Fotograma {ui.frameIndex >= 0 ? ui.frameIndex : '—'}</span>
            </p>
          )}
        </div>

        <aside className="sus-readout">
          <div className={`sus-angle${ui.leftDeg != null ? claseEstado(statusForLeft(ejercicio)) : ''}`}>
            <p className="sus-angle__side">Rodilla izquierda</p>
            <p className={`sus-angle__deg${ui.leftDeg == null ? ' is-empty' : ''}`}>
              {formatearGrados(ui.leftDeg)}
            </p>
          </div>

          <div className={`sus-angle${ui.rightDeg != null ? claseEstado(statusForRight(ejercicio)) : ''}`}>
            <p className="sus-angle__side">Rodilla derecha</p>
            <p className={`sus-angle__deg${ui.rightDeg == null ? ' is-empty' : ''}`}>
              {formatearGrados(ui.rightDeg)}
            </p>
          </div>

          <div className="sus-asym">
            <p className="sus-card__label" style={{ color: 'var(--sus-accent-dark)' }}>
              Asimetría bilateral
            </p>
            <p className="sus-asym__value">{formatearGrados(asimetria)}</p>
            <p className="sus-note" style={{ color: 'var(--sus-text-soft)' }}>
              {asimetria == null
                ? 'A la espera de medición.'
                : asimetriaInterpretable
                  ? 'Por encima del piso de ruido del estimador (≈ 5°).'
                  : 'Dentro del piso de ruido medido (≈ 5°): no es interpretable.'}
            </p>
          </div>

          <p className="sus-note">
            Flexión: 0° equivale a extensión completa; el valor crece al flexionar. El cálculo se
            realiza sobre coordenadas métricas tridimensionales.
          </p>
        </aside>
      </div>
    </main>
  );
}
