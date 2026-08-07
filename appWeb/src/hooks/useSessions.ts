import { useCallback, useState } from 'react';
import { readAccessToken } from '../lib/prefs';
import { buildSessionsListHttpUrl } from '../lib/wsUri';

export function useSessions(apiBase: string) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const token = readAccessToken();
    if (!token) {
      setLoading(false);
      setError('No hay token. Abre Perfil y pulsa «Obtener token».');
      setRows([]);
      return;
    }
    try {
      const res = await fetch(buildSessionsListHttpUrl(apiBase), {
        headers: { Authorization: `Bearer ${token}` },
        signal: AbortSignal.timeout(8000),
      });
      if (res.status === 401) {
        setError('401 — token inválido o expirado.');
        setRows([]);
        return;
      }
      if (res.status === 503) {
        setError('503 — servicio de datos no disponible.');
        setRows([]);
        return;
      }
      if (!res.ok) {
        setError(`HTTP ${res.status}`);
        setRows([]);
        return;
      }
      const decoded = (await res.json()) as unknown;
      const list = Array.isArray(decoded) ? decoded : [];
      setRows(list.map((e) => ({ ...(e as object) } as Record<string, unknown>)));
    } catch (e) {
      setError(String(e));
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [apiBase]);

  return { loading, error, rows, load };
}
