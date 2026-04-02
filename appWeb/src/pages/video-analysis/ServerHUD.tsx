// ServerHUD — compact technical readout for the main column's Zona A (HUD).
// Shows pipeline timing, frame progress and quality flags.
// All values use DM Mono for instant numeric scanning.

interface ServerHUDProps {
  serverPipelineTotalMs: number | null;
  frameIndex: number;
  totalFrames: number | null;
  qualityFlags: string[];
  /** Sin margen inferior (p. ej. dentro de un modal). */
  embedded?: boolean;
}

export function ServerHUD({
  serverPipelineTotalMs,
  frameIndex,
  totalFrames,
  qualityFlags,
  embedded = false,
}: ServerHUDProps) {
  const pipelineLabel = serverPipelineTotalMs != null ? `${serverPipelineTotalMs} ms` : '—';
  const frameLabel =
    frameIndex >= 0
      ? `${frameIndex + 1}${totalFrames != null ? ` / ${totalFrames}` : ''}`
      : '—';

  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '0.5rem 1.25rem',
        padding: '0.625rem 0.875rem',
        background: 'var(--bm-surface)',
        borderRadius: 'var(--bm-radius-md)',
        border: '1px solid var(--bm-border)',
        marginBottom: embedded ? 0 : '0.875rem',
        fontSize: '0.8rem',
      }}
    >
      <HudStat label="Pipeline" value={pipelineLabel} />
      <HudStat label="Frame" value={frameLabel} />
      {qualityFlags.length > 0 && (
        <HudStat label="Calidad" value={qualityFlags.join(', ')} wide />
      )}
    </div>
  );
}

function HudStat({
  label,
  value,
  wide,
}: {
  label: string;
  value: string;
  wide?: boolean;
}) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'baseline',
        gap: '0.4rem',
        ...(wide ? { flexBasis: '100%' } : {}),
      }}
    >
      <span
        style={{
          fontFamily: 'var(--bm-font-body)',
          fontSize: '0.75rem',
          fontWeight: 600,
          color: 'var(--bm-text-secondary)',
          letterSpacing: '0.04em',
          textTransform: 'uppercase',
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontFamily: 'var(--bm-font-mono)',
          fontSize: '0.8125rem',
          color: 'var(--bm-text-primary)',
        }}
      >
        {value}
      </span>
    </div>
  );
}
