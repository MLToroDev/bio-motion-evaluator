import type { CSSProperties } from 'react';

/** Consejos sobre encuadre (modo cámara / web). */
export const LIVE_POSE_TIPS = [
  'Posición de frente a la cámara',
  'Hombro, codo y muñeca visibles',
  'Usa buena iluminación',
  'Mantén el brazo visible en cámara',
] as const;

/** Consejos breves cuando la fuente es vídeo en servidor. */
export const FILE_PREVIEW_TIPS = [
  'Vista previa procesada en el servidor',
  'Revisa ángulos y fase de repetición en el panel',
  'La calidad del JPEG puede afectar el esqueleto',
] as const;

const hudPill: CSSProperties = {
  background: 'rgba(12, 14, 18, 0.78)',
  backdropFilter: 'blur(10px)',
  WebkitBackdropFilter: 'blur(10px)',
  border: '1px solid rgba(255, 255, 255, 0.1)',
  borderRadius: 'var(--bm-radius-sm)',
  fontFamily: 'var(--bm-font-body)',
  pointerEvents: 'none',
};

export interface VideoPreviewOverlaysProps {
  /** Si es false no se pinta nada (p. ej. placeholder vacío). */
  visible: boolean;
  /** Etiqueta corta del modo, p. ej. WEB o SERVIDOR. */
  modeLabel: string;
  /**
   * Tasa de fotogramas/respuestas recibidas por segundo (como en el HUD de referencia).
   * null muestra "—".
   */
  rxPerSec: number | null;
  /** Texto junto al número (por defecto imita “FPS” del mock; en vivo es RX/s del servidor). */
  rateSuffix?: string;
  bullets?: readonly string[];
  /** Añade líneas derivadas de flags del servidor (calidad, etc.). */
  qualityFlags?: string[];
}

export function VideoPreviewOverlays({
  visible,
  modeLabel,
  rxPerSec,
  rateSuffix = 'RX/s',
  bullets = LIVE_POSE_TIPS,
  qualityFlags = [],
}: VideoPreviewOverlaysProps) {
  if (!visible) return null;

  const rateStr = rxPerSec != null ? rxPerSec.toFixed(1) : '—';
  const extra =
    qualityFlags.length > 0
      ? qualityFlags.slice(0, 4)
      : [];

  return (
    <div
      aria-hidden
      style={{
        position: 'absolute',
        inset: 0,
        zIndex: 12,
        pointerEvents: 'none',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '0.65rem 0.75rem',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
        <div style={{ ...hudPill, display: 'flex', alignItems: 'center', gap: '0.45rem', padding: '0.35rem 0.65rem' }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden style={{ color: 'var(--bm-accent)' }}>
            <path
              d="M13 2L3 14h8l-1 8 10-12h-8l1-8z"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinejoin="round"
            />
          </svg>
          <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.15 }}>
            <span style={{ fontFamily: 'var(--bm-font-mono)', fontSize: '0.95rem', fontWeight: 600, color: 'var(--bm-text-primary)' }}>
              {rateStr}
            </span>
            <span style={{ fontSize: '0.62rem', fontWeight: 600, letterSpacing: '0.06em', color: 'var(--bm-text-secondary)', textTransform: 'uppercase' }}>
              {rateSuffix}
            </span>
          </div>
        </div>

        <div
          style={{
            ...hudPill,
            padding: '0.4rem 0.7rem',
            fontSize: '0.68rem',
            fontWeight: 700,
            letterSpacing: '0.08em',
            color: 'var(--bm-text-secondary)',
            textTransform: 'uppercase',
          }}
        >
          Modo: <span style={{ color: 'var(--bm-accent)' }}>{modeLabel}</span>
        </div>
      </div>

      <div style={{ alignSelf: 'flex-start', maxWidth: 'min(100%, 280px)' }}>
        <div
          style={{
            ...hudPill,
            padding: '0.55rem 0.7rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.45rem',
          }}
        >
          {bullets.map((line) => (
            <div key={line} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.45rem', fontSize: '0.72rem', color: 'rgba(255,255,255,0.88)', lineHeight: 1.35 }}>
              <span style={{ marginTop: '0.2rem', width: 5, height: 5, borderRadius: '50%', background: 'var(--bm-accent)', flexShrink: 0 }} />
              <span>{line}</span>
            </div>
          ))}
          {extra.map((line) => (
            <div key={line} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.45rem', fontSize: '0.68rem', color: 'var(--bm-angle-warn)', lineHeight: 1.35 }}>
              <span style={{ marginTop: '0.15rem', flexShrink: 0 }}>⚠</span>
              <span>{line}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
