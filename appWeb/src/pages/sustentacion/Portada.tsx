import { Link } from 'react-router-dom';

/** Pantalla de apertura de la sustentación: identidad y pregunta de investigación. */
export default function Portada() {
  return (
    <main className="sus__main">
      <p className="sus-eyebrow">Trabajo de grado · Ingeniería en Software</p>

      <h1 className="sus-h1">
        Bio-Motion Evaluator
        <br />
        <span style={{ color: 'var(--sus-text-soft)', fontWeight: 500 }}>
          Goniometría digital de rodilla mediante visión artificial
        </span>
      </h1>

      <p className="sus-lead">
        Un sistema cliente-servidor que mide el ángulo de flexión de rodilla a partir de la cámara,
        sin sensores físicos. Este trabajo no se limita a construirlo: lo <strong>mide</strong>.
      </p>

      <div className="sus-question">
        <p className="sus-eyebrow" style={{ marginBottom: '0.75rem' }}>
          Pregunta de investigación
        </p>
        <p>
          ¿Con qué <strong>exactitud</strong>, frente a un método de referencia de medición angular,
          estima el ángulo de flexión de rodilla una arquitectura cliente-servidor con inferencia de
          pose en el servidor, y bajo qué <strong>latencia</strong> entrega en tiempo real ese ángulo
          y la asimetría bilateral sobre hardware de consumo?
        </p>
      </div>

      <p className="sus-lead">
        Es una pregunta verificable: su respuesta no es una descripción del sistema, sino magnitudes
        medidas que pueden contrastarse, reproducirse y refutarse.
      </p>

      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', margin: '2rem 0 0' }}>
        <Link to="/sustentacion/demo" className="sus-btn sus-btn--primary">
          Iniciar demostración
        </Link>
        <Link to="/sustentacion/resultados" className="sus-btn sus-btn--outline">
          Ver resultados
        </Link>
      </div>

      <hr className="sus-divider" />

      <p className="sus-eyebrow" style={{ marginBottom: '0.75rem' }}>
        Manuales
      </p>
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', margin: '0 0 2rem' }}>
        <a
          href={`${import.meta.env.BASE_URL}manuales/manual_usuario.pdf`}
          download
          className="sus-btn sus-btn--outline"
        >
          Descargar manual de usuario (PDF)
        </a>
        <a
          href={`${import.meta.env.BASE_URL}manuales/manual_instalacion.pdf`}
          download
          className="sus-btn sus-btn--outline"
        >
          Descargar manual de instalación (PDF)
        </a>
      </div>

      <div className="sus-grid">
        <div className="sus-card">
          <p className="sus-card__label">Autor</p>
          <p className="sus-card__foot" style={{ fontSize: '0.95rem', color: 'var(--sus-text)' }}>
            Mateo Londoño Toro
          </p>
        </div>
        <div className="sus-card">
          <p className="sus-card__label">Institución</p>
          <p className="sus-card__foot" style={{ fontSize: '0.95rem', color: 'var(--sus-text)' }}>
            Tecnológico de Antioquia
            <br />
            <span style={{ color: 'var(--sus-text-soft)' }}>Facultad de Ingeniería</span>
          </p>
        </div>
        <div className="sus-card">
          <p className="sus-card__label">Arquitectura</p>
          <p className="sus-card__foot" style={{ fontSize: '0.95rem', color: 'var(--sus-text)' }}>
            React · FastAPI · MediaPipe
            <br />
            <span style={{ color: 'var(--sus-text-soft)' }}>Inferencia en servidor</span>
          </p>
        </div>
      </div>
    </main>
  );
}
