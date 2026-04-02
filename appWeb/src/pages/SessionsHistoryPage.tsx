import { useEffect } from 'react';
import { useSessions } from '../hooks/useSessions';
import { readApiBase } from '../lib/prefs';

export default function SessionsHistoryPage() {
  const apiBase = readApiBase();
  const { loading, error, rows, load } = useSessions(apiBase);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div>
      <h1 className="bm-screen-title">Historial de sesiones</h1>
      <button type="button" onClick={() => void load()} disabled={loading} style={{ margin: '12px 0' }}>
        {loading ? 'Cargando…' : 'Actualizar'}
      </button>
      {error && <p style={{ color: 'var(--bm-angle-warn)' }}>{error}</p>}
      {!loading && !error && rows.length === 0 && <p className="bm-caption">No hay sesiones.</p>}
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {rows.map((r, i) => (
          <li
            key={i}
            style={{
              padding: 12,
              borderBottom: '1px solid var(--bm-border)',
              fontSize: '0.85rem',
            }}
          >
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(r, null, 2)}</pre>
          </li>
        ))}
      </ul>
    </div>
  );
}
