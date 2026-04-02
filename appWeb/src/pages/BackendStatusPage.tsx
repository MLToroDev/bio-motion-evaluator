import { useEffect, useState } from 'react';
import { BmButton } from '../components/BmButton';
import { BmInput } from '../components/BmInput';
import { MetricTile } from '../components/MetricTile';
import { readApiBase } from '../lib/prefs';
import { buildHealthHttpUrl } from '../lib/wsUri';

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
      <BmInput label="URL base" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
      <BmButton variant="outline" onClick={() => void check()} loading={loading} style={{ marginBottom: 'var(--bm-space-md)' }}>
        Comprobar /api/v1/health
      </BmButton>
      <MetricTile label="Latencia" value={latencyMs != null ? `${latencyMs} ms` : '—'} status={latencyStatus(latencyMs)} />
      {error && <p className="bm-caption" style={{ color: 'var(--bm-angle-warn)', marginTop: 'var(--bm-space-md)' }}>{error}</p>}
      {health && (
        <pre
          className="bm-caption bm-mono"
          style={{
            marginTop: 'var(--bm-space-md)',
            padding: 'var(--bm-space-sm)',
            background: 'var(--bm-surface)',
            borderRadius: 'var(--bm-radius-md)',
            border: '1px solid var(--bm-border)',
            overflow: 'auto',
            color: 'var(--bm-text-secondary)',
          }}
        >
          {JSON.stringify(health, null, 2)}
        </pre>
      )}
      <p className="bm-caption" style={{ marginTop: 'var(--bm-space-md)' }}>
        <a href={baseUrl} target="_blank" rel="noreferrer" style={{ color: 'var(--bm-accent)' }}>
          Abrir API en navegador
        </a>
      </p>
    </div>
  );
}
