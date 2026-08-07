import {
  buildVideoDownloadCleanupUrl,
  buildVideoDownloadPostUrl,
  buildVideoDownloadStatusUrl,
} from './wsUri';

export class VideoDownloadApiException extends Error {
  statusCode?: number;

  constructor(message: string, statusCode?: number) {
    super(message);
    this.name = 'VideoDownloadApiException';
    this.statusCode = statusCode;
  }
}

export interface VideoDownloadEnqueueResult {
  jobId: string;
  status: string;
  message: string;
}

export interface VideoDownloadStatusResult {
  jobId: string;
  status: string;
  filePath?: string | null;
  errorMessage?: string | null;
}

function fastApiDetail(body: string): string | null {
  try {
    const decoded = JSON.parse(body) as { detail?: unknown };
    const d = decoded.detail;
    if (typeof d === 'string') return d;
    if (Array.isArray(d)) {
      return d.map((e) => (e && typeof e === 'object' && 'msg' in e ? String((e as { msg?: string }).msg) : String(e))).join('; ');
    }
  } catch {
    /* noop */
  }
  return null;
}

const TIMEOUT_MS = 30_000;

export async function enqueueVideoDownload(
  apiBase: string,
  videoUrl: string,
  quality = 'best',
): Promise<VideoDownloadEnqueueResult> {
  const url = buildVideoDownloadPostUrl(apiBase);
  const ac = new AbortController();
  const tid = setTimeout(() => ac.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body: JSON.stringify({ url: videoUrl.trim(), quality }),
      signal: ac.signal,
    });
    if (res.status === 202) {
      const map = (await res.json()) as { job_id?: string; status?: string; message?: string };
      return {
        jobId: String(map.job_id),
        status: String(map.status ?? 'pending'),
        message: String(map.message ?? ''),
      };
    }
    const text = await res.text();
    throw new VideoDownloadApiException(fastApiDetail(text) ?? `HTTP ${res.status}`, res.status);
  } finally {
    clearTimeout(tid);
  }
}

export async function fetchVideoDownloadStatus(
  apiBase: string,
  jobId: string,
): Promise<VideoDownloadStatusResult> {
  const url = buildVideoDownloadStatusUrl(apiBase, jobId);
  const ac = new AbortController();
  const tid = setTimeout(() => ac.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(url, { signal: ac.signal });
    if (res.status === 200) {
      const map = (await res.json()) as {
        job_id?: string;
        status?: string;
        file_path?: string | null;
        error_message?: string | null;
      };
      return {
        jobId: String(map.job_id),
        status: String(map.status ?? 'unknown'),
        filePath: map.file_path,
        errorMessage: map.error_message,
      };
    }
    const text = await res.text();
    throw new VideoDownloadApiException(fastApiDetail(text) ?? `HTTP ${res.status}`, res.status);
  } finally {
    clearTimeout(tid);
  }
}

export async function cleanupVideoDownload(apiBase: string, jobId: string): Promise<void> {
  const url = buildVideoDownloadCleanupUrl(apiBase, jobId);
  const ac = new AbortController();
  const tid = setTimeout(() => ac.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(url, { method: 'DELETE', signal: ac.signal });
    if (res.status !== 200) {
      const text = await res.text();
      throw new VideoDownloadApiException(fastApiDetail(text) ?? `HTTP ${res.status}`, res.status);
    }
  } finally {
    clearTimeout(tid);
  }
}
