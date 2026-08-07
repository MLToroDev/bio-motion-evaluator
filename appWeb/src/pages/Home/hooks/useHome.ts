import { useEffect, useState } from 'react';
import { useBackendHealth } from '../../../hooks/useBackendHealth';
import { readApiBase, readLastSessionSummary } from '../../../lib/prefs';

export function useHome() {
  const [apiBase, setApiBase] = useState(() => readApiBase());
  const [lastSession, setLastSession] = useState<string | null>(null);
  const { ok, loading, ping } = useBackendHealth(apiBase, { intervalMs: 30_000, autoStart: true });

  useEffect(() => {
    setApiBase(readApiBase());
    setLastSession(readLastSessionSummary());
  }, []);

  const badgeStatus = (loading ? 'checking' : ok ? 'connected' : 'disconnected') as 'checking' | 'connected' | 'disconnected';

  return { apiBase, lastSession, ok, loading, ping, badgeStatus };
}
