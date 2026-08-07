import type { ExerciseCatalogEntry } from '../lib/exerciseCatalog';
import type { DetectedObjectPayload, ExerciseValidationPayload } from '../lib/poseWsPayload';

const VALIDATION_CHIP: Record<
  string,
  { label: string; color: string; border: string; bg: string }
> = {
  confirm: {
    label: 'Confirmado',
    color: 'var(--bm-angle-good, #1a7f4e)',
    border: 'var(--bm-angle-good, #1a7f4e)',
    bg: 'color-mix(in srgb, var(--bm-angle-good, #1a7f4e) 12%, transparent)',
  },
  reject: {
    label: 'Rechazado',
    color: 'var(--bm-angle-bad, #b42318)',
    border: 'var(--bm-angle-bad, #b42318)',
    bg: 'color-mix(in srgb, var(--bm-angle-bad, #b42318) 12%, transparent)',
  },
  changed: {
    label: 'Cambio de ejercicio',
    color: 'var(--bm-accent)',
    border: 'var(--bm-accent)',
    bg: 'color-mix(in srgb, var(--bm-accent) 12%, transparent)',
  },
  uncertain: {
    label: 'Incierta',
    color: 'var(--bm-text-secondary)',
    border: 'var(--bm-border)',
    bg: 'var(--bm-background)',
  },
};

/**
 * Bloque hero del ejercicio detectado (análisis en vivo).
 * Enriquecido con metadatos del catálogo / exercises-dataset (GIF opcional).
 */
export function DetectedExerciseHero({
  transmitting,
  labelId,
  title,
  confidence,
  repPhase,
  repCount,
  entry,
  attribution,
  equipmentLabel,
  detectedObjects = [],
  exerciseValidation = null,
}: {
  transmitting: boolean;
  labelId: string;
  title: string;
  confidence: number;
  repPhase: string;
  repCount: number;
  entry: ExerciseCatalogEntry | null;
  attribution?: string;
  equipmentLabel?: string | null;
  detectedObjects?: DetectedObjectPayload[];
  exerciseValidation?: ExerciseValidationPayload | null;
}) {
  if (!transmitting) return null;

  const pct = Math.min(100, Math.max(0, confidence * 100));
  const showUnknown = !labelId || labelId === 'unknown';
  const chip = exerciseValidation ? VALIDATION_CHIP[exerciseValidation.verdict] : null;

  return (
    <section
      aria-live="polite"
      style={{
        display: 'grid',
        gridTemplateColumns: entry?.gif_url ? 'minmax(0, 1fr) 120px' : '1fr',
        gap: 'var(--bm-space-md)',
        alignItems: 'center',
        padding: 'var(--bm-space-md)',
        marginBottom: 'var(--bm-space-md)',
        borderRadius: 'var(--bm-radius-md)',
        border: '1px solid var(--bm-border)',
        background: 'var(--bm-surface)',
      }}
    >
      <div style={{ minWidth: 0 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.45rem' }}>
          <p
            className="bm-caption"
            style={{
              margin: 0,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: 'var(--bm-text-disabled)',
              fontWeight: 700,
            }}
          >
            Ejercicio detectado
          </p>
          {chip ? (
            <span
              className="bm-caption"
              title={
                exerciseValidation
                  ? `${exerciseValidation.reason}${
                      exerciseValidation.validator_label
                        ? ` · teacher: ${exerciseValidation.validator_label}`
                        : ''
                    }`
                  : undefined
              }
              style={{
                padding: '0.15rem 0.45rem',
                borderRadius: 'var(--bm-radius-sm)',
                border: `1px solid ${chip.border}`,
                background: chip.bg,
                color: chip.color,
                fontWeight: 700,
                letterSpacing: '0.04em',
                textTransform: 'uppercase',
                fontSize: '0.68rem',
              }}
            >
              {chip.label}
            </span>
          ) : null}
        </div>
        <h2
          className="bm-screen-title"
          style={{
            margin: '0.25rem 0 0.35rem',
            fontSize: 'clamp(1.35rem, 3.5vw, 1.85rem)',
            lineHeight: 1.15,
            color: showUnknown ? 'var(--bm-text-secondary)' : 'var(--bm-text-primary)',
          }}
        >
          {title}
        </h2>
        <p className="bm-caption" style={{ margin: 0, color: 'var(--bm-text-secondary)' }}>
          Confianza {pct.toFixed(0)}% · Fase {repPhase} · Reps {repCount}
          {equipmentLabel
            ? ` · Equipo: ${equipmentLabel}`
            : entry?.equipment
              ? ` · Equipo catálogo: ${entry.equipment}`
              : ''}
          {entry?.target_muscle ? ` · Enfoque: ${entry.target_muscle}` : ''}
        </p>
        {detectedObjects.length > 0 ? (
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '0.35rem',
              marginTop: '0.55rem',
            }}
          >
            {detectedObjects.slice(0, 6).map((o, i) => (
              <span
                key={`${o.label}-${i}`}
                className="bm-caption"
                style={{
                  padding: '0.2rem 0.5rem',
                  borderRadius: 'var(--bm-radius-sm)',
                  border: '1px solid var(--bm-border)',
                  background: 'var(--bm-background)',
                  color: 'var(--bm-text-primary)',
                }}
              >
                {o.label_es || o.label} {Math.round(o.confidence * 100)}%
              </span>
            ))}
          </div>
        ) : null}
        {entry?.instructions_es ? (
          <p
            className="bm-caption"
            style={{
              margin: '0.55rem 0 0',
              color: 'var(--bm-text-secondary)',
              lineHeight: 1.4,
              maxWidth: 520,
            }}
          >
            {entry.instructions_es}
          </p>
        ) : null}
        {attribution ? (
          <p
            className="bm-caption"
            style={{ margin: '0.45rem 0 0', fontSize: '0.68rem', color: 'var(--bm-text-disabled)' }}
          >
            Ref. visual: {attribution}
          </p>
        ) : null}
      </div>
      {entry?.gif_url ? (
        <img
          src={entry.gif_url}
          alt={entry.external_name || title}
          width={120}
          height={120}
          loading="lazy"
          style={{
            width: 120,
            height: 120,
            objectFit: 'cover',
            borderRadius: 'var(--bm-radius-sm)',
            border: '1px solid var(--bm-border)',
            background: 'var(--bm-background)',
          }}
        />
      ) : null}
    </section>
  );
}
