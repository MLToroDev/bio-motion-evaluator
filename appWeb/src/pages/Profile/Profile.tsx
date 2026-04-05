import { BmButton } from '../../components/BmButton';
import { BmInput } from '../../components/BmInput';
import { useAuth } from '../../hooks/useAuth';
import { readApiBase } from '../../lib/prefs';

export default function Profile() {
  const apiBase = readApiBase();
  const { email, setEmail, tokenPreview, busy, message, fetchToken, logout } = useAuth(apiBase);

  return (
    <div style={{ maxWidth: 480 }}>
      <h1 className="bm-screen-title">Perfil</h1>
      <p className="bm-caption" style={{ marginBottom: 'var(--bm-space-md)' }}>
        Token: <span className="bm-mono">{tokenPreview}</span>
      </p>
      <BmInput label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
      <div style={{ display: 'flex', gap: 'var(--bm-space-sm)', flexWrap: 'wrap', marginTop: 'var(--bm-space-sm)' }}>
        <BmButton variant="primary" disabled={busy} loading={busy} onClick={() => void fetchToken()}>
          Obtener token
        </BmButton>
        <BmButton variant="outline" onClick={logout}>
          Cerrar sesión local
        </BmButton>
      </div>
      {message && <p className="bm-body" style={{ marginTop: 'var(--bm-space-md)' }}>{message}</p>}
    </div>
  );
}
