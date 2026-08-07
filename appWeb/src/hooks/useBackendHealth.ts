import { useCallback, useEffect, useRef, useState } from 'react';
import { buildHealthHttpUrl } from '../lib/wsUri';

export function useBackendHealth(apiBase: string, options?: { intervalMs?: number; autoStart?: boolean }) {
  const intervalMs = options?.intervalMs ?? 30_000;
  const autoStart = options?.autoStart ?? true;
  const [ok, setOk] = useState(false);
  const [loading, setLoading] = useState(false);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);

  const ping = useCallback(async () => {
    setLoading(true);
    const t0 = performance.now();
    try {
      const res = await fetch(buildHealthHttpUrl(apiBase), { signal: AbortSignal.timeout(5000) });
      const ms = Math.round(performance.now() - t0);
      setLatencyMs(ms);
      if (!res.ok) {
        setOk(false);
        return;
      }
      const data = (await res.json()) as { status?: string };
      setOk(data.status === 'ok');
    } catch {
      setOk(false);
      setLatencyMs(null);
    } finally {
      setLoading(false);
    }
  }, [apiBase]);

  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    if (!autoStart) return;
    void ping();
    const id = setInterval(() => {
      if (mounted.current) void ping();
    }, intervalMs);
    return () => clearInterval(id);
  }, [apiBase, autoStart, intervalMs, ping]);

  return { ok, loading, latencyMs, ping };
}
