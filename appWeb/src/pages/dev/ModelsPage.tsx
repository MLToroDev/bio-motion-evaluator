import { useCallback, useEffect, useState } from 'react';
import { BmButton } from '../../components/BmButton';
import { devApiFetch } from '../../lib/devLearningApi';
import { readApiBase } from '../../lib/prefs';
import './devPages.css';

type ModelItem = {
  key: string;
  path: string | null;
  classes: string[] | null;
  window_size: number | null;
  created_at: string | null;
  note: string | null;
  is_active: boolean;
};

export default function ModelsPage() {
  const [active, setActive] = useState<string | null>(null);
  const [items, setItems] = useState<ModelItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await devApiFetch('/models');
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setActive(data.active ?? null);
      setItems(data.items || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const activate = async (key: string) => {
    setBusyKey(key);
    try {
      const res = await devApiFetch(`/models/${encodeURIComponent(key)}/activate`, { method: 'POST', body: '{}' });
      if (!res.ok) throw new Error(await res.text());
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusyKey(null);
    }
  };

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
