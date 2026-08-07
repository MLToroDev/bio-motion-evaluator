/** Normaliza origen del API (misma semántica que `normalizeApiBaseUrl` en Flutter). */
export function normalizeApiBaseUrl(input: string): string {
  let url = input.trim();
  if (!url) return 'http://localhost:8000';
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    url = `http://${url}`;
  }
  while (url.endsWith('/')) {
    url = url.slice(0, -1);
  }
  return url;
}

function websocketPathPrefixFromApiBase(u: URL): string {
  let p = u.pathname;
  if (p === '/' || !p) return '';
  while (p.endsWith('/')) p = p.slice(0, -1);
  const suffix = '/api/v1';
  if (p.endsWith(suffix)) {
    p = p.slice(0, -suffix.length);
    while (p.endsWith('/')) p = p.slice(0, -1);
  }
  return p;
}

export function buildBackendWebSocketUri(baseUrl: string, path: string): string {
  const u = new URL(normalizeApiBaseUrl(baseUrl));
  const scheme = u.protocol === 'https:' ? 'wss:' : 'ws:';
  const rel = path.startsWith('/') ? path : `/${path}`;
  const prefix = websocketPathPrefixFromApiBase(u);
  const fullPath = prefix ? `${prefix}${rel}` : rel;
  const port = u.port ? `:${u.port}` : '';
  return `${scheme}//${u.hostname}${port}${fullPath}`;
}

export function buildPoseStreamWebSocketUri(baseUrl: string): string {
  return buildBackendWebSocketUri(baseUrl, '/ws/pose-stream');
}

export function buildGoldStandardVideosHttpUrl(baseUrl: string): string {
  const u = new URL(normalizeApiBaseUrl(baseUrl));
  const port = u.port ? `:${u.port}` : '';
  return `${u.protocol}//${u.hostname}${port}/api/v1/analysis/gold-standard-videos`;
}

function apiOrigin(baseUrl: string): string {
  const u = new URL(normalizeApiBaseUrl(baseUrl));
  const port = u.port ? `:${u.port}` : '';
  return `${u.protocol}//${u.hostname}${port}`;
}

export function buildHealthHttpUrl(baseUrl: string): string {
  return `${apiOrigin(baseUrl)}/api/v1/health`;
}

export function buildAuthTokenHttpUrl(baseUrl: string): string {
  return `${apiOrigin(baseUrl)}/api/v1/auth/token`;
}

export function buildSessionsListHttpUrl(baseUrl: string): string {
  return `${apiOrigin(baseUrl)}/api/v1/sessions`;
}

export function buildVideoDownloadPostUrl(baseUrl: string): string {
  return `${apiOrigin(baseUrl)}/api/v1/download`;
}

export function buildVideoDownloadStatusUrl(baseUrl: string, jobId: string): string {
  return `${apiOrigin(baseUrl)}/api/v1/download/status/${encodeURIComponent(jobId)}`;
}

export function buildVideoDownloadFileUrl(baseUrl: string, jobId: string): string {
  return `${apiOrigin(baseUrl)}/api/v1/download/file/${encodeURIComponent(jobId)}`;
}

export function buildVideoDownloadCleanupUrl(baseUrl: string, jobId: string): string {
  return `${apiOrigin(baseUrl)}/api/v1/download/cleanup/${encodeURIComponent(jobId)}`;
}

export function buildVideoWebSocketUri(baseUrl: string): string {
  return buildBackendWebSocketUri(baseUrl, '/ws/video');
}
