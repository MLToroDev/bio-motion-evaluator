import { NavLink, Outlet } from 'react-router-dom';
import './AppLayout.css';

const links = [
  { to: '/', label: 'Inicio', end: true },
  { to: '/live-analysis', label: 'Análisis en vivo' },
  { to: '/video-analysis', label: 'Análisis de video' },
  { to: '/video-download', label: 'Descarga de video' },
  { to: '/login', label: 'Iniciar sesión' },
  { to: '/sessions', label: 'Historial sesiones' },
  { to: '/profile', label: 'Perfil' },
  { to: '/backend-status', label: 'Diagnóstico' },
  { to: '/settings/connection', label: 'Configuración' },
];

export default function AppLayout() {
  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="app-sidebar__brand">BIO-MOTION</div>
        {links.map(({ to, label, end }) => (
          <NavLink key={to} to={to} end={end} className={({ isActive }) => (isActive ? 'active' : '')}>
            {label}
          </NavLink>
        ))}
      </aside>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
