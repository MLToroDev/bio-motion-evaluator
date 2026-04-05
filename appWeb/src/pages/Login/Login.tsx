import { Link } from 'react-router-dom';
import { BmButton } from '../../components/BmButton';
import { BmInput } from '../../components/BmInput';
import { useLogin } from './hooks/useLogin';

export default function Login() {
  const { email, setEmail, password, setPassword, busy, msg, signIn } = useLogin();

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
