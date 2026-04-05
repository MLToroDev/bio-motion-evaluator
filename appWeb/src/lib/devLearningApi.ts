import { readApiBase, readDevApiKey } from './prefs';

/** Prefijo de rutas de administración del aprendizaje continuo. */
export function devApiUrl(path: string): string {
  const base = readApiBase();
  const p = path.startsWith('/') ? path : `/${path}`;
  return `${base}/api/v1/dev${p}`;
}

export async function devApiFetch(path: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers);
  const key = readDevApiKey();
  if (key) headers.set('X-Dev-API-Key', key);
  if (init?.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  return fetch(devApiUrl(path), { ...init, headers });
}
