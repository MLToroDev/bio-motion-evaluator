import type { CSSProperties, ReactNode } from 'react';
import type { PreviewFpsAllowed } from '../../lib/previewStreamConfig';
import {
  PREVIEW_FPS_ALLOWED,
  PREVIEW_JPEG_QUALITY_MAX,
  PREVIEW_JPEG_QUALITY_MIN,
} from '../../lib/previewStreamConfig';

export interface ConfigValues {
  apiBase: string;
  videoFilename: string;
  fpsText: string;
  includePreview: boolean;
  captureOnly: boolean;
  serverDiagnostics: boolean;
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

/** Bloque de formulario con título en mayúsculas y línea inferior como divisor entre secciones. */
function PanelSection({
  title,
  divider,
  children,
}: {
  title: string;
  /** Línea bajo el bloque (progressive disclosure: secciones claramente separadas). */
  divider?: boolean;
  children: ReactNode;
}) {
  return (
    <div
      style={{
        marginBottom: divider ? '1rem' : 0,
        paddingBottom: divider ? '1rem' : 0,
        borderBottom: divider ? '1px solid var(--bm-border)' : undefined,
      }}
    >
      <p
        style={{
          fontSize: '0.6875rem',
          fontWeight: 700,
          letterSpacing: '0.07em',
          textTransform: 'uppercase',
          color: 'var(--bm-text-disabled)',
          margin: '0 0 0.625rem',
          fontFamily: 'var(--bm-font-body)',
        }}
      >
        {title}
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>{children}</div>
    </div>
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
  children,
}: {
  label: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
      <FieldLabel>{label}</FieldLabel>
      {children}
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
}: ConfigPanelProps) {
  return (
    <aside
      style={{
        background: 'var(--bm-surface)',
        borderRadius: 'var(--bm-radius-md)',
        border: '1px solid var(--bm-border)',
        padding: '1rem 1.1rem',
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100%',
      }}
    >
      <div style={{ flex: '1 1 auto', minHeight: 0, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <PanelSection title="Fuente" divider>
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

          <Field label="Target FPS" error={fpsParsedError}>
            <input
              style={inputStyle}
              value={values.fpsText}
              onChange={(e) => onChange('fpsText', e.target.value)}
              disabled={running}
            />
          </Field>
        </PanelSection>

        <PanelSection title="Opciones" divider>
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
            label="Vista solo esqueleto"
            checked={values.skeletonOnly}
            onChange={(v) => onChange('skeletonOnly', v)}
            disabled={running}
          />
        </PanelSection>

        <PanelSection title="Calidad de preview">
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
        </PanelSection>
      </div>

      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '0.5rem',
          marginTop: 'auto',
          paddingTop: '1rem',
          borderTop: '1px solid var(--bm-border)',
        }}
      >
        <button
          type="button"
          disabled={!formValid}
          onClick={onStart}
          style={{
            fontFamily: 'var(--bm-font-body)',
            fontSize: '0.875rem',
            fontWeight: 700,
            padding: '0.5rem 0.875rem',
            borderRadius: 'var(--bm-radius-sm)',
            border: '1px solid var(--bm-accent-dim)',
            background: 'var(--bm-accent)',
            color: '#000',
            cursor: formValid ? 'pointer' : 'not-allowed',
            opacity: formValid ? 1 : 0.42,
            transition: 'opacity 120ms',
          }}
        >
          Iniciar análisis
        </button>

        <button
          type="button"
          disabled={!running}
          onClick={onStop}
          style={{
            fontFamily: 'var(--bm-font-body)',
            fontSize: '0.875rem',
            padding: '0.5rem 0.875rem',
            borderRadius: 'var(--bm-radius-sm)',
            border: '1px solid var(--bm-border)',
            background: 'var(--bm-surface-elevated)',
            color: 'var(--bm-text-primary)',
            cursor: running ? 'pointer' : 'not-allowed',
            opacity: running ? 1 : 0.42,
          }}
        >
          Detener
        </button>

        <button
          type="button"
          disabled={!csvReady}
          onClick={onDownloadCsv}
          style={{
            fontFamily: 'var(--bm-font-body)',
            fontSize: '0.875rem',
            padding: '0.5rem 0.875rem',
            borderRadius: 'var(--bm-radius-sm)',
            border: '1px solid var(--bm-border)',
            background: 'transparent',
            color: csvReady ? 'var(--bm-text-secondary)' : 'var(--bm-text-disabled)',
            cursor: csvReady ? 'pointer' : 'not-allowed',
          }}
        >
          Descargar CSV
        </button>
      </div>

      {statusError && (
        <p
          style={{
            margin: '0.5rem 0 0',
            fontSize: '0.8125rem',
            color: 'var(--bm-angle-bad)',
            fontFamily: 'var(--bm-font-body)',
          }}
        >
          {statusError}
        </p>
      )}
    </aside>
  );
}
