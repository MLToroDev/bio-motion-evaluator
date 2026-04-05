import { useEffect, useState } from 'react';
import { readApiBase } from '../../../lib/prefs';
import { buildHealthHttpUrl } from '../../../lib/wsUri';

export function latencyStatus(ms: number | null): 'good' | 'warn' | 'bad' | 'neutral' {
  if (ms == null) return 'neutral';
  if (ms < 100) return 'good';
  if (ms < 500) return 'warn';
  return 'bad';
}

export function useBackendStatus() {
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

  return { baseUrl, setBaseUrl, loading, error, health, latencyMs, check };
}
