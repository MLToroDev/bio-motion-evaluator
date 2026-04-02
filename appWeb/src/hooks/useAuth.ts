import { useCallback, useEffect, useState } from 'react';
import { buildAuthTokenHttpUrl } from '../lib/wsUri';
import { clearAuthPrefs, persistAuthTokenAndEmail, readAccessToken, readSavedUserEmail } from '../lib/prefs';

export function useAuth(apiBase: string) {
  const [tokenPreview, setTokenPreview] = useState<string>('—');
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = useCallback(() => {
    const tok = readAccessToken();
    setTokenPreview(tok && tok.length > 12 ? `${tok.slice(0, 12)}…` : tok ?? '—');
    const m = readSavedUserEmail();
    if (m) setEmail(m);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const fetchToken = useCallback(async () => {
    setBusy(true);
    setMessage(null);
    const mail = email.trim() || 'anonymous@local.test';
    try {
      const res = await fetch(buildAuthTokenHttpUrl(apiBase), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: mail }),
        signal: AbortSignal.timeout(8000),
      });
      if (res.status === 503) {
        setMessage('503 — sin base de datos en el servidor; auth no disponible.');
        return;
      }
      if (!res.ok) {
        setMessage(`HTTP ${res.status}: ${await res.text()}`);
        return;
      }
      const map = (await res.json()) as { access_token?: string };
      const token = map.access_token;
      if (!token) {
        setMessage('Respuesta sin access_token');
        return;
      }
      persistAuthTokenAndEmail(token, mail);
      setMessage('Token guardado.');
      setTokenPreview(`${token.slice(0, 12)}…`);
    } catch (e) {
      setMessage(String(e));
    } finally {
      setBusy(false);
    }
  }, [apiBase, email]);

  const logout = useCallback(() => {
    clearAuthPrefs();
    setTokenPreview('—');
    setMessage('Sesión cerrada localmente.');
  }, []);

  return { email, setEmail, tokenPreview, busy, message, setMessage, fetchToken, logout, refresh };
}
