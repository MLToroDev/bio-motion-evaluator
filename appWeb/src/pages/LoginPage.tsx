import { useState } from 'react';
import { Link } from 'react-router-dom';
import { BmButton } from '../components/BmButton';
import { BmInput } from '../components/BmInput';
import { readApiBase } from '../lib/prefs';
import { buildAuthTokenHttpUrl } from '../lib/wsUri';

export default function LoginPage() {
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

  return (
    <div style={{ maxWidth: 400 }}>
      <h1 className="bm-screen-title">Iniciar sesión</h1>
      <p className="bm-caption" style={{ marginBottom: 'var(--bm-space-lg)' }}>
        El backend stub emite JWT con <code>POST /api/v1/auth/token</code>. Para persistencia completa usa{' '}
        <Link to="/profile" style={{ color: 'var(--bm-accent)' }}>
          Perfil
        </Link>
        .
      </p>
      <BmInput label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
      <BmInput label="Contraseña (reservado)" type="password" value={password} onChange={(e) => setPassword(e.target.value)} disabled />
      <BmButton variant="primary" disabled={busy} loading={busy} onClick={() => void signIn()}>
        Solicitar token (stub)
      </BmButton>
      {msg && <p className="bm-body" style={{ marginTop: 'var(--bm-space-md)', color: 'var(--bm-text-secondary)' }}>{msg}</p>}
    </div>
  );
}
