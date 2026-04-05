import { BmButton } from '../../../components/BmButton';
import { readApiBase } from '../../../lib/prefs';
import '../devPages.css';
import { useDevModels } from './hooks/useDevModels';

export default function Models() {
  const { active, items, error, busyKey, load, activate } = useDevModels();
  const hfBase = 'https://huggingface.co';

  return (
    <div className="bm-dev-page bm-dev-page--narrow">
      <h1 className="bm-screen-title">Modelos ONNX (manifest)</h1>
      <p className="bm-caption" style={{ marginBottom: 'var(--bm-space-md)' }}>
        Activo en runtime: <strong style={{ color: 'var(--bm-text-primary)' }}>{active || '(ninguno — heurístico)'}</strong>.
        <span className="bm-mono" style={{ display: 'block', marginTop: 'var(--bm-space-xs)' }}>
          API: {readApiBase()}
        </span>
      </p>
      {error ? <p className="bm-caption bm-dev-msg--error">{error}</p> : null}
      <BmButton variant="outline" type="button" onClick={() => void load()} style={{ marginBottom: 'var(--bm-space-md)' }}>
        Refrescar
      </BmButton>
      <ul className="bm-dev-list-plain">
        {items.map((m) => (
          <li key={m.key} className="bm-dev-card">
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--bm-space-sm)' }}>
              <span style={{ fontSize: '0.9375rem', fontWeight: 600 }}>{m.key}</span>
              {m.is_active ? (
                <span className="bm-section-header" style={{ margin: 0, color: 'var(--bm-accent)' }}>
                  Activo
                </span>
              ) : (
                <BmButton variant="primary" type="button" disabled={busyKey === m.key} onClick={() => void activate(m.key)}>
                  Activar
                </BmButton>
              )}
            </div>
            {m.path ? (
              <p className="bm-caption bm-mono" style={{ margin: 'var(--bm-space-sm) 0 0', whiteSpace: 'pre-wrap' }}>
                {m.path}
              </p>
            ) : null}
            <p className="bm-caption" style={{ margin: 'var(--bm-space-xs) 0 0' }}>
              Clases: {(m.classes || []).join(', ') || '—'}
            </p>
            {m.note ? (
              <p className="bm-caption" style={{ margin: 'var(--bm-space-xs) 0 0', color: 'var(--bm-text-disabled)' }}>
                {m.note}
              </p>
            ) : null}
          </li>
        ))}
      </ul>
      <p className="bm-caption" style={{ marginTop: 'var(--bm-space-xl)' }}>
        <a className="bm-dev-link" href={hfBase} target="_blank" rel="noreferrer">
          Hugging Face Hub
        </a>{' '}
        — configura <span className="bm-dev-code-inline">HF_MODEL_REPO_ID</span> en el servidor para publicar artefactos desde
        jobs de entrenamiento.
      </p>
    </div>
  );
}
