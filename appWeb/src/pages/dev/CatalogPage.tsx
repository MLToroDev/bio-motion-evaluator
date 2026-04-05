import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BmButton } from '../../components/BmButton';
import { devApiFetch } from '../../lib/devLearningApi';
import './devPages.css';

type CatalogExercise = {
  id: string;
  display_es?: string;
  description_es?: string;
};

type Stats = {
  by_label: Record<string, { pending: number; approved: number; rejected: number }>;
  totals: { pending: number; approved: number; rejected: number; all: number };
};

export default function CatalogPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<{
    exercises: CatalogExercise[];
    stats: Stats | null;
    last_f1_per_class: Record<string, number>;
  } | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await devApiFetch('/catalog');
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || res.statusText);
      }
      setData(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setData(null);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="bm-dev-page">
      <h1 className="bm-screen-title">Catálogo de ejercicios (Dev)</h1>
      <p className="bm-caption" style={{ marginBottom: 'var(--bm-space-md)' }}>
        Resumen del catálogo y muestras aprobadas por etiqueta. Pulsa una tarjeta para abrir el dataset filtrado.
      </p>
      {error ? (
        <p className="bm-caption bm-dev-msg--error">
          {error}
          <span className="bm-caption" style={{ display: 'block', marginTop: 'var(--bm-space-xs)' }}>
            ¿DATABASE_URL activa y migraciones aplicadas? ¿API key en Configuración?
          </span>
        </p>
      ) : null}
      <div className="bm-dev-catalog-head">
        <BmButton variant="outline" type="button" onClick={() => void load()}>
          Actualizar
        </BmButton>
      </div>
      {!data ? (
        !error && <p className="bm-caption">Cargando…</p>
      ) : (
        <div className="bm-dev-catalog-grid">
          {data.exercises.map((ex) => {
            const st = data.stats?.by_label[ex.id] || { pending: 0, approved: 0, rejected: 0 };
            const f1 = data.last_f1_per_class[ex.id];
            return (
              <button
                key={ex.id}
                type="button"
                className="bm-dev-catalog-card"
                onClick={() => navigate(`/dev/dataset?label=${encodeURIComponent(ex.id)}`)}
              >
                <div className="bm-dev-catalog-card__title">{ex.display_es || ex.id}</div>
                <div className="bm-dev-catalog-card__id">{ex.id}</div>
                <div className="bm-dev-catalog-card__stats">
                  Aprobadas: <strong style={{ color: 'var(--bm-accent)' }}>{st.approved}</strong> · Pend.: {st.pending} ·
                  Rech.: {st.rejected}
                </div>
                {f1 != null && Number.isFinite(f1) ? (
                  <div className="bm-dev-catalog-card__f1">Último F1 (val): {f1.toFixed(3)}</div>
                ) : null}
              </button>
            );
          })}
        </div>
      )}
      {data?.stats?.totals ? (
        <p className="bm-dev-stat-foot">
          Total muestras: {data.stats.totals.all} (aprobadas {data.stats.totals.approved})
        </p>
      ) : null}
    </div>
  );
}
