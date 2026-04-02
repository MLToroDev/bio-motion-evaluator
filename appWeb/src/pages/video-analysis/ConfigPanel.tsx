import type { CSSProperties, ReactNode } from 'react';
import type { PreviewFpsAllowed } from '../../lib/previewStreamConfig';
import {
  PREVIEW_FPS_ALLOWED,
  PREVIEW_JPEG_QUALITY_MAX,
  PREVIEW_JPEG_QUALITY_MIN,
} from '../../lib/previewStreamConfig';
import { VideoAnalysisActions } from './VideoAnalysisActions';

export interface ConfigValues {
  apiBase: string;
  videoFilename: string;
  fpsText: string;
  /** Sin limitar FPS en el servidor (máximo rendimiento posible). */
  maxThroughput: boolean;
  includePreview: boolean;
  captureOnly: boolean;
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

          <CheckRow
            label="Máximo rendimiento (sin limitar FPS en servidor)"
            checked={values.maxThroughput}
            onChange={(v) => onChange('maxThroughput', v)}
            disabled={running}
          />
          <Field
            label="Target FPS"
            error={values.maxThroughput ? undefined : fpsParsedError}
            hint={
              values.maxThroughput
                ? 'Opción desactivada: el backend procesa cada frame tan pronto como pueda.'
                : undefined
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
            disabled={running}
          />
          <CheckRow
            label="Vista solo esqueleto"
            checked={values.skeletonOnly}
            onChange={(v) => onChange('skeletonOnly', v)}
            disabled={running}
          />
        </ConfigCard>

        <ConfigCard title="Calidad de preview">
          <Field label="Preview FPS">
            <select
              style={inputStyle}
              value={values.previewFps}
              onChange={(e) => onChange('previewFps', Number(e.target.value) as PreviewFpsAllowed)}
              disabled={!values.includePreview}
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
