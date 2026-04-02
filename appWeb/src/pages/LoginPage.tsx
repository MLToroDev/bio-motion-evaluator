import { useState } from 'react';
import { Link } from 'react-router-dom';
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
      <p className="bm-caption" style={{ marginBottom: 24 }}>
        El backend stub emite JWT con <code>POST /api/v1/auth/token</code>. Para persistencia completa usa{' '}
        <Link to="/profile">Perfil</Link>.
      </p>
      <label className="field" style={{ display: 'block', marginBottom: 12 }}>
        <span>Email</span>
        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={{ width: '100%', padding: 8, marginTop: 4, borderRadius: 8, border: '1px solid var(--bm-border)', background: 'var(--bm-surface)', color: 'inherit' }}
        />
      </label>
      <label className="field" style={{ display: 'block', marginBottom: 16 }}>
        <span>Contraseña (reservado)</span>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled
          style={{ width: '100%', padding: 8, marginTop: 4, borderRadius: 8, opacity: 0.5 }}
        />
      </label>
      <button type="button" className="primary" disabled={busy} onClick={() => void signIn()}>
        {busy ? '…' : 'Solicitar token (stub)'}
      </button>
      {msg && <p style={{ marginTop: 16, color: 'var(--bm-text-secondary)' }}>{msg}</p>}
    </div>
  );
}
