import { useCallback, useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import './AppLayout.css';

const SIDEBAR_COLLAPSED_KEY = 'bm-sidebar-collapsed';

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

function readSidebarCollapsed(): boolean {
  try {
    return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === '1';
  } catch {
    return false;
  }
}

export default function AppLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(readSidebarCollapsed);

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(SIDEBAR_COLLAPSED_KEY, next ? '1' : '0');
      } catch {
        /* noop */
      }
      return next;
    });
  }, []);

  return (
    <div className={`app-shell${sidebarCollapsed ? ' app-shell--sidebar-collapsed' : ''}`}>
      <aside className={`app-sidebar${sidebarCollapsed ? ' app-sidebar--collapsed' : ''}`} aria-hidden={sidebarCollapsed}>
        <div className="app-sidebar__header">
          <div className="app-sidebar__brand">BIO-MOTION</div>
          <button
            type="button"
            className="app-sidebar__toggle"
            onClick={toggleSidebar}
            aria-label="Ocultar menú lateral"
            aria-expanded={!sidebarCollapsed}
            title="Ocultar menú"
          >
            <ChevronLeftIcon aria-hidden />
          </button>
        </div>
        {links.map(({ to, label, end }) => (
          <NavLink key={to} to={to} end={end} className={({ isActive }) => (isActive ? 'active' : '')}>
            {label}
          </NavLink>
        ))}
      </aside>

      {sidebarCollapsed && (
        <button
          type="button"
          className="app-sidebar__reveal"
          onClick={toggleSidebar}
          aria-label="Mostrar menú lateral"
          title="Mostrar menú"
        >
          <ChevronRightIcon aria-hidden />
        </button>
      )}

      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}

function ChevronLeftIcon({ 'aria-hidden': ah }: { 'aria-hidden'?: boolean }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden={ah}>
      <path d="M15 18l-6-6 6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ChevronRightIcon({ 'aria-hidden': ah }: { 'aria-hidden'?: boolean }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden={ah}>
      <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
