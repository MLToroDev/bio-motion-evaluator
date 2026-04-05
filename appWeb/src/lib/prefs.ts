/** Mismas claves que Flutter `home_prefs` / `auth_prefs`. */
export const Prefs = {
  apiBase: 'bio_api_base',
  lastSession: 'bio_last_session',
  targetRepGoal: 'bio_target_rep_goal',
  accessToken: 'bio_access_token',
  userEmail: 'bio_user_email',
  /** Cabecera opcional X-Dev-API-Key para rutas `/api/v1/dev/*`. */
  devApiKey: 'bm_dev_api_key',
} as const;

function safeGet(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSet(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* noop */
  }
}

export function readApiBase(fallback = 'http://localhost:8000'): string {
  const s = safeGet(Prefs.apiBase)?.trim();
  if (s) {
    let url = s;
    if (!url.startsWith('http://') && !url.startsWith('https://')) url = `http://${url}`;
    while (url.endsWith('/')) url = url.slice(0, -1);
    return url;
  }
  return fallback;
}

export function persistApiBase(baseUrl: string): void {
  let url = baseUrl.trim();
  if (!url.startsWith('http://') && !url.startsWith('https://')) url = `http://${url}`;
  while (url.endsWith('/')) url = url.slice(0, -1);
  safeSet(Prefs.apiBase, url);
}

export function readLastSessionSummary(): string | null {
  const s = safeGet(Prefs.lastSession)?.trim();
  return s || null;
}

export function persistLastSessionSummary(line: string): void {
  safeSet(Prefs.lastSession, line);
}

export function readTargetRepGoal(): number | null {
  const s = safeGet(Prefs.targetRepGoal)?.trim();
  if (!s) return null;
  const n = parseInt(s, 10);
  if (!Number.isFinite(n) || n <= 0) return null;
  return n;
}

export function persistTargetRepGoal(goal: number | null): void {
  if (goal == null || goal <= 0) safeSet(Prefs.targetRepGoal, '');
  else safeSet(Prefs.targetRepGoal, String(goal));
}

export function readAccessToken(): string | null {
  const s = safeGet(Prefs.accessToken)?.trim();
  return s || null;
}

export function readSavedUserEmail(): string | null {
  const s = safeGet(Prefs.userEmail)?.trim();
  return s || null;
}

export function persistAuthTokenAndEmail(token: string, email: string): void {
  safeSet(Prefs.accessToken, token);
  safeSet(Prefs.userEmail, email.trim());
}

export function clearAuthPrefs(): void {
  safeSet(Prefs.accessToken, '');
  safeSet(Prefs.userEmail, '');
}

export function readDevApiKey(): string | null {
  const s = safeGet(Prefs.devApiKey)?.trim();
  return s || null;
}

export function persistDevApiKey(key: string): void {
  safeSet(Prefs.devApiKey, key.trim());
}
