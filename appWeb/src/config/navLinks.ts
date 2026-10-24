import { flags } from './featureFlags';

export type NavLinkDef = {
  to: string;
  label: string;
  end?: boolean;
  tier: 'core' | 'sprint4';
};

const CORE_LINKS: NavLinkDef[] = [
  { to: '/inicio', label: 'Inicio', end: true, tier: 'core' },
  // Interfaz de sustentación (tema claro, mínima). Vive fuera de este layout
  // y tiene su propia navegación; ver src/pages/sustentacion/.
  { to: '/sustentacion', label: 'Modo sustentación', tier: 'core' },
  { to: '/live-analysis', label: 'Análisis en vivo', tier: 'core' },
  { to: '/video-analysis', label: 'Análisis de video', tier: 'core' },
  { to: '/backend-status', label: 'Diagnóstico', tier: 'core' },
  { to: '/settings/connection', label: 'Configuración', tier: 'core' },
];

const SPRINT4_LINKS: NavLinkDef[] = [
  { to: '/video-download', label: 'Descarga de video', tier: 'sprint4' },
  { to: '/login', label: 'Iniciar sesión', tier: 'sprint4' },
  { to: '/sessions', label: 'Historial sesiones', tier: 'sprint4' },
  { to: '/profile', label: 'Perfil', tier: 'sprint4' },
];

export function getSidebarLinks(sprint4UiEnabled: boolean): NavLinkDef[] {
  const out: NavLinkDef[] = [...CORE_LINKS];
  if (flags.showSprint4 && sprint4UiEnabled) out.push(...SPRINT4_LINKS);
  return out;
}

export const SPRINT4_PATHS = new Set(SPRINT4_LINKS.map((l) => l.to));
