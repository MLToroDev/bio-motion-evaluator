import { useState } from 'react';
import { readApiBase } from '../../../lib/prefs';
import { buildAuthTokenHttpUrl } from '../../../lib/wsUri';

export function useLogin() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const signIn = async () => {
    setBusy(true);
    setMsg(null);
    const base = readApiBase();
    try {
      const res = await fetch(buildAuthTokenHttpUrl(base), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim() || 'anonymous@local.test',
        }),
        signal: AbortSignal.timeout(8000),
      });
      if (res.ok) {
        setMsg('Token obtenido. Revisa Perfil para verlo guardado o usa «Obtener token» allí.');
      } else {
        setMsg(`HTTP ${res.status}: ${await res.text()}`);
      }
    } catch (e) {
      setMsg(String(e));
    } finally {
      setBusy(false);
    }
  };

  return { email, setEmail, password, setPassword, busy, msg, signIn };
}
