import { useAuth } from '../hooks/useAuth';
import { readApiBase } from '../lib/prefs';

export default function ProfilePage() {
  const apiBase = readApiBase();
  const { email, setEmail, tokenPreview, busy, message, fetchToken, logout } = useAuth(apiBase);

  return (
    <div style={{ maxWidth: 480 }}>
      <h1 className="bm-screen-title">Perfil</h1>
      <p className="bm-caption" style={{ marginBottom: 16 }}>
        Token: <span className="bm-mono">{tokenPreview}</span>
      </p>
      <label className="field" style={{ display: 'block', marginBottom: 12 }}>
        <span>Email</span>
        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={{ width: '100%', padding: 8, marginTop: 4, borderRadius: 8, border: '1px solid var(--bm-border)', background: 'var(--bm-surface)', color: 'inherit' }}
        />
      </label>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button type="button" className="primary" disabled={busy} onClick={() => void fetchToken()}>
          {busy ? '…' : 'Obtener token'}
        </button>
        <button type="button" onClick={logout}>
          Cerrar sesión local
        </button>
      </div>
      {message && <p style={{ marginTop: 16 }}>{message}</p>}
    </div>
  );
}
