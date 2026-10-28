/**
 * Resultados medidos del trabajo de grado.
 *
 * Las cifras proceden de los experimentos reproducibles de `validacion/`
 * y coinciden con el § 7 de la memoria. Lo que no se midió se declara
 * como pendiente y no se presenta como resultado. El Nivel 2 (Tracker)
 * sale de `validacion/resultados/nivel2_acuerdo.md`: su veredicto
 * preregistrado es «no concluyente» y sus cifras son descriptivas.
 */
export default function Resultados() {
  return (
    <main className="sus__main">
      <p className="sus-eyebrow">Resultados</p>
      <h1 className="sus-h1" style={{ fontSize: 'clamp(1.5rem, 2.6vw, 2rem)' }}>
        Qué se midió y qué salió
      </h1>
      <p className="sus-lead">
        Cuatro experimentos reproducibles sobre <strong>7 877 fotogramas</strong> de vídeo y
        barridos analíticos de verdad conocida. Hardware de medición: Apple M5, MediaPipe 0.10.35.
      </p>

      {/* ─── Exactitud ─── */}
      <h2 className="sus-h2" style={{ marginTop: '2.5rem' }}>1 · Exactitud</h2>
      <p className="sus-lead">
        El error del sistema se descompone en dos fuentes. Acotar la primera permite atribuir el
        resto a la estimación de pose.
      </p>

      <div className="sus-grid">
        <div className="sus-card sus-card--good">
          <p className="sus-card__label">Error del cálculo angular</p>
          <p className="sus-card__value">≈ 0<span className="sus-card__unit">grados</span></p>
          <p className="sus-card__foot">
            <strong>6×10⁻⁷ grados</strong> en el peor caso frente a ángulos de verdad conocida:
            siete órdenes de magnitud por debajo del error de la goniometría manual. La aritmética
            no contribuye al error del sistema.
          </p>
        </div>

        <div className="sus-card sus-card--warn">
          <p className="sus-card__label">Defecto detectado y corregido</p>
          <p className="sus-card__value">32<span className="sus-card__unit">grados</span></p>
          <p className="sus-card__foot">
            Sesgo sistemático que arrastraba el sistema por calcular sobre coordenadas anisótropas.
            Se anulaba justo en 90°, por eso pasó inadvertido.
          </p>
        </div>

        <div className="sus-card">
          <p className="sus-card__label">Tolerancia de cámara</p>
          <p className="sus-card__value">20<span className="sus-card__unit">grados máx.</span></p>
          <p className="sus-card__foot">
            Desalineación máxima respecto del plano sagital admitida por el protocolo de captura.
          </p>
        </div>

        <div className="sus-card">
          <p className="sus-card__label">Piso de ruido de la asimetría</p>
          <p className="sus-card__value">5<span className="sus-card__unit">grados</span></p>
          <p className="sus-card__foot">
            Por debajo de esta cota la asimetría bilateral no es distinguible del ruido del propio
            estimador.
          </p>
        </div>
      </div>

      {/* ─── Latencia ─── */}
      <h2 className="sus-h2" style={{ marginTop: '2.75rem' }}>2 · Latencia y rendimiento</h2>
      <p className="sus-lead">
        El cuello de botella no estaba donde se suponía.
      </p>

      <div className="sus-grid">
        <div className="sus-card sus-card--good">
          <p className="sus-card__label">Capacidad sostenida</p>
          <p className="sus-card__value">126<span className="sus-card__unit">fps</span></p>
          <p className="sus-card__foot">
            8,32 ms por fotograma (p95) sin regulador. El preset actual usa el 11 % de esa
            capacidad.
          </p>
        </div>

        <div className="sus-card">
          <p className="sus-card__label">Inferencia de pose</p>
          <p className="sus-card__value">93,4<span className="sus-card__unit">%</span></p>
          <p className="sus-card__foot">
            Del presupuesto por fotograma. El cálculo biomecánico consume el 0,3 %: es
            prácticamente gratis.
          </p>
        </div>

        <div className="sus-card sus-card--warn">
          <p className="sus-card__label">Ocio por regulador de ritmo</p>
          <p className="sus-card__value">89<span className="sus-card__unit">%</span></p>
          <p className="sus-card__foot">
            A 10 FPS objetivo el servidor duerme 89 de cada 100 ms. El retraso percibido era una
            decisión de configuración, no un límite del hardware.
          </p>
        </div>
      </div>

      {/* ─── Referencia externa (Nivel 2) ─── */}
      <h2 className="sus-h2" style={{ marginTop: '2.75rem' }}>3 · Validación con referencia externa</h2>
      <p className="sus-lead">
        Protocolo preregistrado, ejecutado y reportado completo: 75 fotogramas medidos a mano en
        Tracker y 26 repetidos días después para acotar el error del propio comparador.
      </p>

      <div className="sus-grid">
        <div className="sus-card sus-card--warn">
          <p className="sus-card__label">Validación con referencia externa (Tracker)</p>
          <p className="sus-card__value">No concluyente</p>
          <p className="sus-card__foot">
            Concordancia excelente (<strong>ICC 0,978</strong>) y error medio de{' '}
            <strong>8,1 grados</strong> en el ángulo 3D, con sesgo que depende del rango. El
            comparador manual se repitió con 3,07 grados de error frente a los 3,0 exigidos, así
            que según el criterio preregistrado el resultado <strong>no es concluyente</strong> y
            esas cifras son solo descriptivas.
          </p>
          <p className="sus-card__foot">
            Exploratorio, no preregistrado: el ángulo 2D del plano de la imagen difiere de Tracker
            4,2 grados de media; buena parte de la diferencia viene de comparar un ángulo 3D con su
            proyección 2D.
          </p>
        </div>
      </div>

      {/* ─── Pendiente ─── */}
      <h2 className="sus-h2" style={{ marginTop: '2.75rem' }}>4 · Lo que no se midió</h2>

      <div className="sus-grid">
        <div className="sus-card sus-card--pending">
          <p className="sus-card__label">Profundidad de MediaPipe</p>
          <p className="sus-card__value">Sin validar</p>
          <p className="sus-card__foot">
            La corrección adoptada es geométricamente correcta, pero la exactitud de la estimación
            de profundidad no se ha contrastado.
          </p>
        </div>
      </div>

      <hr className="sus-divider" />

      {/* ─── Aportación ─── */}
      <h2 className="sus-h2">Aportación</h2>
      <table className="sus-table">
        <thead>
          <tr>
            <th style={{ width: '32%' }}>Elemento</th>
            <th>Por qué importa</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="num">Descomposición del error</td>
            <td>
              Separar el error de la aritmética del de la estimación de pose permite concluir sobre
              la tecnología, no solo sobre esta implementación.
            </td>
          </tr>
          <tr>
            <td className="num">Modo de fallo documentado</td>
            <td>
              Cualquier sistema que calcule ángulos sobre landmarks normalizados de MediaPipe
              arrastra el mismo sesgo. Se anula en 90°, lo que dificulta detectarlo por inspección.
            </td>
          </tr>
          <tr>
            <td className="num">Instrumentación reproducible</td>
            <td>
              Experimentos, módulo estadístico y protocolo quedan ejecutables para extender la
              validación a otras articulaciones sin rehacer la infraestructura.
            </td>
          </tr>
        </tbody>
      </table>

      <p className="sus-note" style={{ marginTop: '1.5rem' }}>
        Detalle completo en el § 7 de la memoria. Datos crudos, figuras y scripts en{' '}
        <code>validacion/</code>.
      </p>
    </main>
  );
}
