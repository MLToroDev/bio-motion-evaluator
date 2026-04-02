import { useEffect, useState } from 'react';
import { MetricTile } from '../components/MetricTile';
import { buildHealthHttpUrl } from '../lib/wsUri';
import { readApiBase } from '../lib/prefs';

function latencyStatus(ms: number | null): 'good' | 'warn' | 'bad' | 'neutral' {
  if (ms == null) return 'neutral';
  if (ms < 100) return 'good';
  if (ms < 500) return 'warn';
  return 'bad';
}

export default function BackendStatusPage() {
  const [baseUrl, setBaseUrl] = useState(() => readApiBase());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);

  const check = async () => {
    setLoading(true);
    setError(null);
    setHealth(null);
    const t0 = performance.now();
    try {
      const res = await fetch(buildHealthHttpUrl(baseUrl), { signal: AbortSignal.timeout(5000) });
      const ms = Math.round(performance.now() - t0);
      setLatencyMs(ms);
      if (res.ok) {
        setHealth((await res.json()) as Record<string, unknown>);
      } else {
        setError(`HTTP ${res.status}`);
      }
    } catch (e) {
      setLatencyMs(Math.round(performance.now() - t0));
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void check();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div style={{ maxWidth: 560 }}>
      <h1 className="bm-screen-title">Conexión al servidor</h1>
      <label className="field" style={{ display: 'block', margin: '16px 0' }}>
        <span>URL base</span>
        <input
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          style={{ width: '100%', padding: 8, marginTop: 4, borderRadius: 8, border: '1px solid var(--bm-border)', background: 'var(--bm-surface)', color: 'inherit' }}
        />
      </label>
      <button type="button" onClick={() => void check()} disabled={loading} style={{ marginBottom: 16 }}>
        {loading ? 'Comprobando…' : 'Comprobar /api/v1/health'}
      </button>
      <MetricTile
        label="Latencia"
        value={latencyMs != null ? `${latencyMs} ms` : '—'}
        status={latencyStatus(latencyMs)}
      />
      {error && <p style={{ color: 'var(--bm-angle-warn)', marginTop: 12 }}>{error}</p>}
      {health && (
        <pre
          style={{
            marginTop: 16,
            padding: 12,
            background: 'var(--bm-surface)',
            borderRadius: 8,
            fontSize: 12,
            overflow: 'auto',
          }}
        >
          {JSON.stringify(health, null, 2)}
        </pre>
      )}
      <p className="bm-caption" style={{ marginTop: 16 }}>
        <a href={baseUrl} target="_blank" rel="noreferrer" style={{ color: 'var(--bm-accent)' }}>
          Abrir API en navegador
        </a>
      </p>
    </div>
  );
}
