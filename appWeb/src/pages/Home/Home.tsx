import { useNavigate } from 'react-router-dom';
import { BmButton } from '../../components/BmButton';
import { LiveIndicatorDot } from '../../components/LiveIndicatorDot';
import { NavCard } from '../../components/NavCard';
import { SectionHeader } from '../../components/SectionHeader';
import { StatusBadge } from '../../components/StatusBadge';
import { useHome } from './hooks/useHome';

export default function Home() {
  const navigate = useNavigate();
  const { apiBase, lastSession, ok, loading, ping, badgeStatus } = useHome();

  return (
    <div>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 'var(--bm-space-md)',
          flexWrap: 'wrap',
          gap: 'var(--bm-space-sm)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--bm-space-md)' }}>
          <LiveIndicatorDot active={ok && !loading} />
          <h1 className="bm-screen-title">Bio-Motion</h1>
        </div>
        <BmButton variant="outline" onClick={() => void ping()}>
          Comprobar backend
        </BmButton>
      </div>
      <p className="bm-hero-title" style={{ margin: '0 0 var(--bm-space-sm)' }}>
        BIO-MOTION
      </p>
      <p className="bm-body" style={{ color: 'var(--bm-text-secondary)', marginBottom: 'var(--bm-space-md)' }}>
        Evaluación biomecánica en tiempo real
      </p>
      <StatusBadge status={badgeStatus} />
      {!ok && !loading && (
        <p className="bm-caption" style={{ marginTop: 'var(--bm-space-md)', color: 'var(--bm-angle-warn)' }}>
          Verifica el servidor en {apiBase}.{' '}
          <button
            type="button"
            style={{ color: 'var(--bm-accent)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
            onClick={() => navigate('/backend-status')}
          >
            Ir al diagnóstico
          </button>
        </p>
      )}

      <SectionHeader>Análisis</SectionHeader>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <NavCard
          primary
          title="Análisis en vivo"
          subtitle="Cámara: pose y ángulos en tiempo real."
          icon="📹"
          onClick={() => navigate('/live-analysis')}
        />
        <NavCard
          title="Análisis de video"
          subtitle="Gold standard en servidor."
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

      <SectionHeader>Desarrollo — aprendizaje del clasificador</SectionHeader>
      <p className="bm-caption" style={{ marginBottom: 8, maxWidth: 520 }}>
        No forma parte del flujo de análisis clínico: dataset, entrenamiento ONNX y manifest. También en el menú lateral bajo «Dev Tools».
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <NavCard
          title="Dev · Fuentes de datos"
          subtitle="Buscar vídeos YouTube e ingestar muestras automáticamente."
          icon="🔍"
          onClick={() => navigate('/dev/sources')}
        />
        <NavCard
          title="Dev · Catálogo"
          subtitle="Ejercicios y conteo de muestras por etiqueta."
          icon="📚"
          onClick={() => navigate('/dev/catalog')}
        />
        <NavCard
          title="Dev · Dataset"
          subtitle="Revisar y aprobar muestras 32D antes de entrenar."
          icon="🗃️"
          onClick={() => navigate('/dev/dataset')}
        />
        <NavCard
          title="Dev · Entrenamiento"
          subtitle="Encolar job Celery (requiere worker + requirements-train)."
          icon="🧠"
          onClick={() => navigate('/dev/training')}
        />
        <NavCard
          title="Dev · Modelos"
          subtitle="Activar versión ONNX en manifest.json."
          icon="⚙️"
          onClick={() => navigate('/dev/models')}
        />
      </div>

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
          padding: 'var(--bm-space-md)',
          background: 'var(--bm-surface)',
          borderRadius: 'var(--bm-radius-md)',
          border: '1px solid var(--bm-border)',
        }}
      >
        <p className="bm-caption">{lastSession ?? 'Aún no hay resumen de sesión guardado.'}</p>
      </div>
      <p className="bm-caption" style={{ textAlign: 'center', marginTop: 'var(--bm-space-xl)' }}>
        Bio-Motion Evaluator · React (appWeb)
      </p>
    </div>
  );
}
