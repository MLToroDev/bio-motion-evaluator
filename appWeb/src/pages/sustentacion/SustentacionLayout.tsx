import { useLayoutEffect } from 'react';
import { Link, NavLink, Outlet } from 'react-router-dom';
import './sustentacion.css';

/**
 * Tokens del esqueleto para el tema claro.
 *
 * `PoseSkeletonCanvas` lee estas variables desde `document.documentElement`
 * al montarse, no del contenedor, de modo que no basta con declararlas en
 * un ámbito CSS local: hay que fijarlas en la raíz mientras esta interfaz
 * esté activa y restaurarlas al salir.
 */
const TOKENS_CLAROS: Record<string, string> = {
  '--bm-skeleton-line': '#2563eb',
  '--bm-skeleton-joint': '#ffffff',
  '--bm-skeleton-joint-border': '#1d4ed8',
};

const ENLACES = [
  { to: '/sustentacion', label: 'Inicio', end: true },
  { to: '/sustentacion/demo', label: 'Demostración', end: false },
  { to: '/sustentacion/resultados', label: 'Resultados', end: false },
];

export default function SustentacionLayout() {
  useLayoutEffect(() => {
    const raiz = document.documentElement;
    const previos = new Map<string, string>();
    for (const [clave, valor] of Object.entries(TOKENS_CLAROS)) {
      previos.set(clave, raiz.style.getPropertyValue(clave));
      raiz.style.setProperty(clave, valor);
    }
    return () => {
      for (const [clave, anterior] of previos) {
        if (anterior) raiz.style.setProperty(clave, anterior);
        else raiz.style.removeProperty(clave);
      }
    };
  }, []);

  return (
    <div className="sus">
      <header className="sus__bar">
        <Link to="/sustentacion" className="sus__brand">
          BIO<span>·</span>MOTION
        </Link>

        <nav className="sus__nav">
          {ENLACES.map(({ to, label, end }) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => (isActive ? 'is-active' : '')}>
              {label}
            </NavLink>
          ))}
        </nav>

        <Link to="/" className="sus__exit" title="Volver a la interfaz completa de desarrollo">
          Interfaz completa →
        </Link>
      </header>

      <Outlet />
    </div>
  );
}
