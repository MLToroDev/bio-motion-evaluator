import { useCallback, useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import { flags } from '../../../config/featureFlags';
import type { PreviewFpsAllowed } from '../../../lib/previewStreamConfig';
import {
  PREVIEW_FPS_ALLOWED,
  PREVIEW_JPEG_QUALITY_MAX,
  PREVIEW_JPEG_QUALITY_MIN,
} from '../../../lib/previewStreamConfig';
import { VideoAnalysisActions } from './VideoAnalysisActions';

export type AnalysisInputSource = 'file' | 'server_camera' | 'browser_camera';

/** Modo de etiqueta de ejercicio enviado al backend (`forced_exercise_label` si no es auto). */
export type VideoExerciseMode = 'auto' | 'idle' | 'squat' | 'lunge';

export interface ConfigValues {
  apiBase: string;
  videoFilename: string;
  /** Índice OpenCV en el host del API (solo modo cámara servidor). */
  serverCameraDeviceIndex: number;
  /** deviceId vacío = cámara por defecto del navegador. */
  browserCameraDeviceId: string;
  inputSource: AnalysisInputSource;
  fpsText: string;
  /** Sin limitar FPS en el servidor (máximo rendimiento posible). */
  maxThroughput: boolean;
  includePreview: boolean;
  captureOnly: boolean;
  exerciseMode: VideoExerciseMode;
  serverDiagnostics: boolean;
  /** Perfil automático según resolución/FPS del clip (backend). */
  streamTuningAuto: boolean;
  skeletonOnly: boolean;
  previewFps: PreviewFpsAllowed;
  previewQuality: number;
}

interface ConfigPanelProps {
  values: ConfigValues;
  onChange: <K extends keyof ConfigValues>(key: K, value: ConfigValues[K]) => void;
  onPersistApi: () => void;
  onRefreshVideos: () => void;
  onStart: () => void;
  onStop: () => void;
  onDownloadCsv: () => void;
  videoList: string[];
  listLoading: boolean;
  listError: string | null;
  fpsParsedError?: string;
  formValid: boolean;
  running: boolean;
  csvReady: boolean;
  statusError: string | null;
  /** Oculta el panel lateral para ampliar el preview (mismo efecto que el toggle del encabezado). */
  onCollapsePanel?: () => void;
}

function FieldLabel({ children }: { children: ReactNode }) {
  return (
    <span
      style={{
        fontSize: '0.8125rem',
        fontWeight: 500,
        color: 'var(--bm-text-secondary)',
        fontFamily: 'var(--bm-font-body)',
      }}
    >
      {children}
    </span>
  );
}

/** Tarjeta autocontenida: agrupa campos relacionados (patrón de tarjetas en columna). */
function ConfigCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section
      style={{
        background: 'var(--bm-surface)',
        border: '1px solid var(--bm-border)',
        borderRadius: 'var(--bm-radius-md)',
        padding: '0.75rem 0.85rem',
        boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)',
      }}
    >
      <h3
        style={{
          fontSize: '0.6875rem',
          fontWeight: 700,
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          color: 'var(--bm-text-disabled)',
          margin: '0 0 0.55rem',
          fontFamily: 'var(--bm-font-body)',
        }}
      >
        {title}
      </h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>{children}</div>
    </section>
  );
}

function CheckRow({
  label,
  checked,
  onChange,
  disabled,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <label
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        fontSize: '0.8125rem',
        color: disabled ? 'var(--bm-text-disabled)' : 'var(--bm-text-primary)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        fontFamily: 'var(--bm-font-body)',
      }}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
        style={{ accentColor: 'var(--bm-accent)', width: 14, height: 14 }}
      />
      {label}
    </label>
  );
}

function Field({
  label,
  error,
  hint,
  children,
}: {
  label: string;
  error?: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
      <FieldLabel>{label}</FieldLabel>
      {children}
      {hint && (
        <span
          style={{
            fontSize: '0.72rem',
            color: 'var(--bm-text-secondary)',
            fontFamily: 'var(--bm-font-body)',
            lineHeight: 1.35,
          }}
        >
          {hint}
        </span>
      )}
      {error && (
        <span
          style={{
            fontSize: '0.75rem',
            color: 'var(--bm-angle-warn)',
            fontFamily: 'var(--bm-font-body)',
          }}
        >
          {error}
        </span>
      )}
    </div>
  );
}

const inputStyle: CSSProperties = {
  fontFamily: 'var(--bm-font-body)',
  fontSize: '0.875rem',
  color: 'var(--bm-text-primary)',
  background: 'var(--bm-background)',
  border: '1px solid var(--bm-border)',
  borderRadius: 'var(--bm-radius-md)',
  padding: '0.45rem 0.6rem',
  width: '100%',
  outline: 'none',
};

function BrowserCameraFields({
  running,
  selectedDeviceId,
  onDeviceChange,
}: {
  running: boolean;
  selectedDeviceId: string;
  onDeviceChange: (deviceId: string) => void;
}) {
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [listBusy, setListBusy] = useState(false);
  const [listErr, setListErr] = useState<string | null>(null);

  const listCameras = useCallback(async () => {
    setListErr(null);
    setListBusy(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      stream.getTracks().forEach((t) => t.stop());
      const all = await navigator.mediaDevices.enumerateDevices();
      const vids = all.filter((d) => d.kind === 'videoinput');
      setDevices(vids);
    } catch (e) {
      setListErr(`Permisos o cámara: ${e}. Usa https o localhost.`);
      setDevices([]);
    } finally {
      setListBusy(false);
    }
  }, []);

  const onPickRef = useRef(onDeviceChange);
  onPickRef.current = onDeviceChange;

  useEffect(() => {
    if (devices.length === 0 || running) return;
    const ok = devices.some((d) => d.deviceId === selectedDeviceId);
    if (!ok && devices[0]) {
      onPickRef.current(devices[0].deviceId);
    }
  }, [devices, selectedDeviceId, running]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <div>
        <button
          type="button"
          onClick={() => void listCameras()}
          disabled={running || listBusy}
          style={{
            fontFamily: 'var(--bm-font-body)',
            fontSize: '0.8125rem',
            padding: '0.4rem 0.7rem',
            borderRadius: 'var(--bm-radius-sm)',
            border: '1px solid var(--bm-border)',
            background: 'var(--bm-surface-elevated)',
            color: 'var(--bm-text-primary)',
            cursor: running || listBusy ? 'not-allowed' : 'pointer',
            opacity: running || listBusy ? 0.5 : 1,
          }}
        >
          {listBusy ? 'Solicitando…' : 'Permitir y listar cámaras'}
        </button>
        {listErr ? (
          <p style={{ margin: '0.4rem 0 0', fontSize: '0.8rem', color: 'var(--bm-angle-bad)' }}>{listErr}</p>
        ) : null}
      </div>
      <Field label="Cámara del navegador">
        <select
          style={inputStyle}
          value={selectedDeviceId}
          onChange={(e) => onDeviceChange(e.target.value)}
          disabled={running || devices.length === 0}
        >
          {devices.length === 0 ? (
            <option value="">— lista primero las cámaras —</option>
          ) : (
            devices.map((d) => (
              <option key={d.deviceId} value={d.deviceId}>
                {d.label || `Cámara ${d.deviceId.slice(0, 8)}…`}
              </option>
            ))
          )}
        </select>
      </Field>
    </div>
  );
}

export function ConfigPanel({
  values,
  onChange,
  onPersistApi,
  onRefreshVideos,
  onStart,
  onStop,
  onDownloadCsv,
  videoList,
  listLoading,
  listError,
  fpsParsedError,
  formValid,
  running,
  csvReady,
  statusError,
  onCollapsePanel,
}: ConfigPanelProps) {
  return (
    <aside
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem',
        minHeight: 0,
        maxHeight: 'calc(100vh - 9.5rem)',
        overflow: 'hidden',
        paddingRight: 0,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.5rem',
          flexShrink: 0,
        }}
      >
        <span
          style={{
            fontSize: '0.8125rem',
            fontWeight: 700,
            color: 'var(--bm-text-secondary)',
            fontFamily: 'var(--bm-font-body)',
          }}
        >
          Parámetros de análisis
        </span>
        {onCollapsePanel ? (
          <button
            type="button"
            onClick={onCollapsePanel}
            aria-label="Ocultar panel y ampliar vista de vídeo"
            title="Ocultar panel"
            style={{
              flexShrink: 0,
              width: '2rem',
              height: '2rem',
              padding: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid var(--bm-border)',
              borderRadius: 'var(--bm-radius-sm)',
              background: 'var(--bm-surface)',
              color: 'var(--bm-text-secondary)',
              cursor: 'pointer',
              fontSize: '0.9rem',
              lineHeight: 1,
            }}
          >
            ◀
          </button>
        ) : null}
      </div>

      <div
        style={{
          flex: '1 1 auto',
          minHeight: 0,
          overflowY: 'auto',
          paddingRight: '0.15rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.75rem',
        }}
      >
        <ConfigCard title="Fuente">
          <Field label="URL base del API">
            <input
              style={inputStyle}
              value={values.apiBase}
              onChange={(e) => onChange('apiBase', e.target.value)}
              onBlur={onPersistApi}
              disabled={running}
              autoComplete="off"
            />
          </Field>

          {flags.showAdvancedVideoConfig ? (
            <Field label="Tipo de fuente">
              <select
                style={inputStyle}
                value={values.inputSource}
                onChange={(e) => onChange('inputSource', e.target.value as AnalysisInputSource)}
                disabled={running}
              >
                <option value="file">Vídeo en servidor (gold standard)</option>
                <option value="server_camera">Webcam del servidor (OpenCV en el API)</option>
                <option value="browser_camera">Webcam de este equipo (navegador)</option>
              </select>
              <span
                style={{
                  fontSize: '0.72rem',
                  color: 'var(--bm-text-secondary)',
                  fontFamily: 'var(--bm-font-body)',
                  lineHeight: 1.35,
                  display: 'block',
                  marginTop: '0.35rem',
                }}
              >
                {values.inputSource === 'server_camera'
                  ? 'El API debe ejecutarse en el PC donde está la webcam; no sirve si el backend está en la nube sin cámara.'
                  : values.inputSource === 'browser_camera'
                    ? 'El vídeo se captura en tu navegador y se envía al API (válido con servidor local o remoto).'
                    : 'Lista de archivos bajo la ruta de vídeos gold standard del backend.'}
              </span>
            </Field>
          ) : (
            <p
              className="bm-caption"
              style={{ margin: 0, color: 'var(--bm-text-secondary)', lineHeight: 1.4 }}
            >
              Vídeo gold standard en el servidor (modo demostración MVP).
            </p>
          )}

          {values.inputSource === 'file' || !flags.showAdvancedVideoConfig ? (
            <>
              <div>
                <button
                  type="button"
                  onClick={onRefreshVideos}
                  disabled={running || listLoading}
                  style={{
                    fontFamily: 'var(--bm-font-body)',
                    fontSize: '0.8125rem',
                    padding: '0.4rem 0.7rem',
                    borderRadius: 'var(--bm-radius-sm)',
                    border: '1px solid var(--bm-border)',
                    background: 'var(--bm-surface-elevated)',
                    color: 'var(--bm-text-primary)',
                    cursor: running || listLoading ? 'not-allowed' : 'pointer',
                    opacity: running || listLoading ? 0.5 : 1,
                  }}
                >
                  {listLoading ? 'Cargando…' : 'Actualizar lista de vídeos'}
                </button>
                {listError && (
                  <p style={{ margin: '0.4rem 0 0', fontSize: '0.8rem', color: 'var(--bm-angle-bad)' }}>
                    {listError}
                  </p>
                )}
              </div>

              <Field label="Vídeo en servidor">
                <select
                  style={inputStyle}
                  value={values.videoFilename}
                  onChange={(e) => onChange('videoFilename', e.target.value)}
                  disabled={running || videoList.length === 0}
                >
                  {videoList.length === 0 ? (
                    <option value="">— sin vídeos —</option>
                  ) : (
                    videoList.map((v) => (
                      <option key={v} value={v}>
                        {v}
                      </option>
                    ))
                  )}
                </select>
              </Field>
            </>
          ) : null}

          {flags.showAdvancedVideoConfig && values.inputSource === 'server_camera' ? (
            <Field
              label="Índice de dispositivo OpenCV"
              hint="0 suele ser la webcam principal en el equipo del API."
            >
              <input
                type="number"
                min={0}
                max={15}
                step={1}
                style={inputStyle}
                value={values.serverCameraDeviceIndex}
                onChange={(e) => {
                  const n = Number(e.target.value);
                  onChange('serverCameraDeviceIndex', Number.isFinite(n) ? Math.max(0, Math.min(15, n)) : 0);
                }}
                disabled={running}
              />
            </Field>
          ) : null}

          {flags.showAdvancedVideoConfig && values.inputSource === 'browser_camera' ? (
            <BrowserCameraFields
              running={running}
              selectedDeviceId={values.browserCameraDeviceId}
              onDeviceChange={(id) => onChange('browserCameraDeviceId', id)}
            />
          ) : null}

          {flags.showAdvancedVideoConfig ? (
            <CheckRow
              label="Máximo rendimiento (sin limitar FPS en servidor)"
              checked={values.maxThroughput}
              onChange={(v) => onChange('maxThroughput', v)}
              disabled={running || values.inputSource === 'browser_camera'}
            />
          ) : null}
          <Field
            label={
              flags.showAdvancedVideoConfig && values.inputSource === 'browser_camera'
                ? 'FPS de envío (navegador → API)'
                : 'Velocidad de análisis (FPS)'
            }
            error={values.maxThroughput ? undefined : fpsParsedError}
            hint={
              flags.showAdvancedVideoConfig
                ? values.maxThroughput
                  ? values.inputSource === 'browser_camera'
                    ? undefined
                    : 'Opción desactivada: el backend procesa cada frame tan pronto como pueda.'
                  : values.inputSource === 'browser_camera'
                    ? 'Intervalo entre JPEG enviados por WebSocket (también limitado por la latencia de red).'
                    : undefined
                : 'Fotogramas por segundo enviados al servidor para inferencia de rodilla.'
            }
          >
            <input
              style={{
                ...inputStyle,
                opacity: values.maxThroughput ? 0.55 : 1,
              }}
              value={values.fpsText}
              onChange={(e) => onChange('fpsText', e.target.value)}
              disabled={running || values.maxThroughput}
            />
          </Field>
        </ConfigCard>

        {flags.showAdvancedVideoConfig ? (
        <ConfigCard title="Opciones">
          <CheckRow
            label="Incluir vista previa JPEG"
            checked={values.includePreview}
            onChange={(v) => onChange('includePreview', v)}
            disabled={running}
          />
          <CheckRow
            label="Solo captura (capture_only)"
            checked={values.captureOnly}
            onChange={(v) => onChange('captureOnly', v)}
            disabled={running}
          />
          <Field
            label="Ejercicio"
            hint={
              values.captureOnly
                ? 'Desactiva «Solo captura» para usar clasificación o forzar etiqueta.'
                : 'Automático: clasificador del servidor. Otras opciones fijan la etiqueta (confianza 1,0).'
            }
          >
            <select
              style={inputStyle}
              value={values.exerciseMode}
              onChange={(e) => onChange('exerciseMode', e.target.value as VideoExerciseMode)}
              disabled={running || values.captureOnly}
            >
              <option value="auto">Automático</option>
              <option value="idle">idle</option>
              <option value="squat">squat</option>
              <option value="lunge">lunge</option>
            </select>
          </Field>
          <CheckRow
            label="Diagnósticos servidor"
            checked={values.serverDiagnostics}
            onChange={(v) => onChange('serverDiagnostics', v)}
            disabled={running}
          />
          <CheckRow
            label="Ajuste automático al vídeo (resolución / FPS)"
            checked={values.streamTuningAuto}
            onChange={(v) => onChange('streamTuningAuto', v)}
            disabled={running || values.inputSource === 'browser_camera'}
          />
          <CheckRow
            label="Vista solo esqueleto"
            checked={values.skeletonOnly}
            onChange={(v) => onChange('skeletonOnly', v)}
            disabled={running}
          />
        </ConfigCard>
        ) : null}

        {flags.showAdvancedVideoConfig ? (
        <ConfigCard title="Calidad de preview">
          <Field
            label="Preview FPS"
            hint={
              values.inputSource === 'browser_camera'
                ? 'Solo aplica al flujo pose-stream (archivo / cámara servidor). En modo navegador usa «FPS de envío».'
                : undefined
            }
          >
            <select
              style={inputStyle}
              value={values.previewFps}
              onChange={(e) => onChange('previewFps', Number(e.target.value) as PreviewFpsAllowed)}
              disabled={!values.includePreview || values.inputSource === 'browser_camera'}
            >
              {PREVIEW_FPS_ALLOWED.map((v) => (
                <option key={v} value={v}>
                  {v} FPS
                </option>
              ))}
            </select>
          </Field>

          <Field
            label={`Calidad JPEG — ${Math.round(values.previewQuality)} (${PREVIEW_JPEG_QUALITY_MIN}–${PREVIEW_JPEG_QUALITY_MAX})`}
            hint={
              values.inputSource === 'browser_camera'
                ? 'Calidad del JPEG que envías al API y de la vista previa local.'
                : undefined
            }
          >
            <input
              type="range"
              min={PREVIEW_JPEG_QUALITY_MIN}
              max={PREVIEW_JPEG_QUALITY_MAX}
              value={values.previewQuality}
              onChange={(e) => onChange('previewQuality', Number(e.target.value))}
              disabled={!values.includePreview}
              style={{ width: '100%', accentColor: 'var(--bm-accent)' } as CSSProperties}
            />
          </Field>
        </ConfigCard>
        ) : null}
      </div>

      {statusError ? (
        <p
          style={{
            margin: 0,
            flexShrink: 0,
            fontSize: '0.8125rem',
            color: 'var(--bm-angle-bad)',
            fontFamily: 'var(--bm-font-body)',
            padding: '0.35rem 0.25rem 0',
          }}
        >
          {statusError}
        </p>
      ) : null}

      <div
        style={{
          flexShrink: 0,
          marginTop: 'auto',
          paddingTop: '0.65rem',
          borderTop: '1px solid var(--bm-border)',
          background: 'linear-gradient(180deg, transparent 0%, var(--bm-background) 28%)',
          boxShadow: '0 -8px 24px rgba(0,0,0,0.25)',
        }}
      >
        <p
          style={{
            fontSize: '0.65rem',
            fontWeight: 700,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: 'var(--bm-text-disabled)',
            margin: '0 0 0.45rem',
            fontFamily: 'var(--bm-font-body)',
          }}
        >
          Acciones
        </p>
        <VideoAnalysisActions
          variant="panel-footer"
          formValid={formValid}
          running={running}
          csvReady={csvReady}
          onStart={onStart}
          onStop={onStop}
          onDownloadCsv={onDownloadCsv}
        />
      </div>
    </aside>
  );
}
