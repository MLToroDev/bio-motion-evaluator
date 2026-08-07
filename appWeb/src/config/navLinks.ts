import { flags } from './featureFlags';

export type NavLinkDef = {
  to: string;
  label: string;
  end?: boolean;
  tier: 'core' | 'sprint4' | 'dev';
};

const CORE_LINKS: NavLinkDef[] = [
  { to: '/', label: 'Inicio', end: true, tier: 'core' },
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

const DEV_LINKS: NavLinkDef[] = [
  { to: '/dev/sources', label: 'Dev · Fuentes de datos', tier: 'dev' },
  { to: '/dev/catalog', label: 'Dev · Catálogo', tier: 'dev' },
  { to: '/dev/dataset', label: 'Dev · Dataset', tier: 'dev' },
  { to: '/dev/training', label: 'Dev · Entrenamiento', tier: 'dev' },
  { to: '/dev/models', label: 'Dev · Modelos', tier: 'dev' },
];

export function getSidebarLinks(sprint4UiEnabled: boolean): NavLinkDef[] {
  const out: NavLinkDef[] = [...CORE_LINKS];
  if (flags.showSprint4 && sprint4UiEnabled) out.push(...SPRINT4_LINKS);
  return out;
}

export function getDevSidebarLinks(): NavLinkDef[] {
  return flags.showDevTools ? DEV_LINKS : [];
}

export const SPRINT4_PATHS = new Set(SPRINT4_LINKS.map((l) => l.to));
export const DEV_PATH_PREFIX = '/dev/';
