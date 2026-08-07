import { BmButton } from '../../components/BmButton';
import { BmInput } from '../../components/BmInput';
import { MetricTile } from '../../components/MetricTile';
import { latencyStatus, useBackendStatus } from './hooks/useBackendStatus';

export default function BackendStatus() {
  const { baseUrl, setBaseUrl, loading, error, health, latencyMs, check } = useBackendStatus();

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
