import { useEffect } from 'react';
import { BmButton } from '../../components/BmButton';
import { useSessions } from '../../hooks/useSessions';
import { readApiBase } from '../../lib/prefs';

export default function SessionsHistory() {
  const apiBase = readApiBase();
  const { loading, error, rows, load } = useSessions(apiBase);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div>
      <h1 className="bm-screen-title">Historial de sesiones</h1>
      <BmButton variant="outline" onClick={() => void load()} loading={loading} style={{ margin: 'var(--bm-space-md) 0' }}>
        Actualizar
      </BmButton>
      {error && <p className="bm-caption" style={{ color: 'var(--bm-angle-warn)' }}>{error}</p>}
      {!loading && !error && rows.length === 0 && <p className="bm-caption">No hay sesiones.</p>}
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {rows.map((r, i) => (
          <li
            key={i}
            style={{
              padding: 'var(--bm-space-sm)',
              borderBottom: '1px solid var(--bm-border)',
            }}
          >
            <pre className="bm-caption bm-mono" style={{ margin: 0, whiteSpace: 'pre-wrap', color: 'var(--bm-text-secondary)' }}>
              {JSON.stringify(r, null, 2)}
            </pre>
          </li>
        ))}
      </ul>
    </div>
  );
}
