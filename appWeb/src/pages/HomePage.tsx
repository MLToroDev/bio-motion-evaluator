import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LiveIndicatorDot } from '../components/LiveIndicatorDot';
import { NavCard } from '../components/NavCard';
import { SectionHeader } from '../components/SectionHeader';
import { useBackendHealth } from '../hooks/useBackendHealth';
import { readApiBase, readLastSessionSummary } from '../lib/prefs';

export default function HomePage() {
  const navigate = useNavigate();
  const [apiBase, setApiBase] = useState(() => readApiBase());
  const [lastSession, setLastSession] = useState<string | null>(null);
  const { ok, loading, ping } = useBackendHealth(apiBase, { intervalMs: 30_000, autoStart: true });

  useEffect(() => {
    setApiBase(readApiBase());
    setLastSession(readLastSessionSummary());
  }, []);

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <LiveIndicatorDot active={ok && !loading} />
          <h1 className="bm-screen-title" style={{ margin: 0 }}>
            Bio-Motion
          </h1>
        </div>
        <button
          type="button"
          onClick={() => void ping()}
          style={{
            background: 'var(--bm-surface-elevated)',
            border: '1px solid var(--bm-border)',
            color: 'var(--bm-text-primary)',
            padding: '8px 12px',
            borderRadius: 8,
            cursor: 'pointer',
          }}
        >
          Comprobar backend
        </button>
      </div>
      <p className="bm-hero-title" style={{ margin: '0 0 8px' }}>
        BIO-MOTION
      </p>
      <p style={{ color: 'var(--bm-text-secondary)', marginBottom: 16 }}>
        Evaluación biomecánica en tiempo real
      </p>
      <div
        style={{
          display: 'inline-block',
          padding: '4px 10px',
          borderRadius: 6,
          border: '1px solid var(--bm-border)',
          background: ok ? 'var(--bm-accent-muted)' : 'var(--bm-surface-elevated)',
          color: ok ? 'var(--bm-accent)' : 'var(--bm-angle-warn)',
          fontSize: '0.8rem',
        }}
      >
        {loading ? 'Comprobando…' : ok ? 'Backend conectado' : 'Sin conexión al backend'}
      </div>
      {!ok && !loading && (
        <p className="bm-caption" style={{ marginTop: 12, color: 'var(--bm-angle-warn)' }}>
          Verifica el servidor en {apiBase}.{' '}
          <button type="button" style={{ color: 'var(--bm-accent)', background: 'none', border: 'none', cursor: 'pointer' }} onClick={() => navigate('/backend-status')}>
            Ir al diagnóstico
          </button>
        </p>
      )}

      <SectionHeader>Análisis</SectionHeader>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <NavCard
          title="Análisis en vivo"
          subtitle="Cámara: pose y ángulos (WebSocket /ws/video)."
          icon="📹"
          onClick={() => navigate('/live-analysis')}
        />
        <NavCard
          title="Análisis de video"
          subtitle="Gold standard en servidor (WebSocket /ws/pose-stream)."
          icon="🎬"
          onClick={() => navigate('/video-analysis')}
        />
      </div>

      <SectionHeader>Herramientas</SectionHeader>
      <NavCard
        title="Descarga remota de vídeo"
        subtitle="Cola en el servidor (yt-dlp)."
        icon="⬇️"
        onClick={() => navigate('/video-download')}
      />

      <SectionHeader>Cuenta</SectionHeader>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <NavCard title="Iniciar sesión" subtitle="Acceso y token JWT." icon="🔐" onClick={() => navigate('/login')} />
        <NavCard title="Historial de sesiones" subtitle="Lista con JWT." icon="📋" onClick={() => navigate('/sessions')} />
        <NavCard title="Perfil" subtitle="Token y cierre de sesión local." icon="👤" onClick={() => navigate('/profile')} />
      </div>

      <SectionHeader>Diagnóstico</SectionHeader>
      <NavCard
        title="Conexión al servidor"
        subtitle="Health, latencia."
        icon="🖧"
        onClick={() => navigate('/backend-status')}
      />

      <SectionHeader>Última sesión</SectionHeader>
      <div
        style={{
          padding: 16,
          background: 'var(--bm-surface)',
          borderRadius: 10,
          border: '1px solid var(--bm-border)',
          fontSize: '0.85rem',
          color: 'var(--bm-text-secondary)',
        }}
      >
        {lastSession ?? 'Aún no hay resumen de sesión guardado.'}
      </div>
      <p className="bm-caption" style={{ textAlign: 'center', marginTop: 32 }}>
        Bio-Motion Evaluator · React (appWeb)
      </p>
    </div>
  );
}
