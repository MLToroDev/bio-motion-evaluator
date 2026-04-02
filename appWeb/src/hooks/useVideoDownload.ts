import { useCallback, useRef, useState } from 'react';
import {
  cleanupVideoDownload,
  enqueueVideoDownload,
  fetchVideoDownloadStatus,
  VideoDownloadApiException,
} from '../lib/videoDownloadApi';
import { buildVideoDownloadFileUrl } from '../lib/wsUri';

export function useVideoDownload(apiBase: string) {
  const [url, setUrl] = useState('');
  const [quality, setQuality] = useState('best');
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPoll = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const enqueue = useCallback(async () => {
    setError(null);
    stopPoll();
    setJobId(null);
    setStatus(null);
    try {
      const r = await enqueueVideoDownload(apiBase, url, quality);
      setJobId(r.jobId);
      setStatus(r.status);
      pollRef.current = setInterval(async () => {
        if (!r.jobId) return;
        try {
          const s = await fetchVideoDownloadStatus(apiBase, r.jobId);
          setStatus(s.status);
          if (s.status === 'completed' || s.status === 'failed') {
            stopPoll();
            if (s.status === 'failed' && s.errorMessage) setError(s.errorMessage);
          }
        } catch (e) {
          stopPoll();
          setError(e instanceof VideoDownloadApiException ? e.message : String(e));
        }
      }, 1500);
    } catch (e) {
      setError(e instanceof VideoDownloadApiException ? e.message : String(e));
    }
  }, [apiBase, url, quality]);

  const fileHref = jobId && status === 'completed' ? buildVideoDownloadFileUrl(apiBase, jobId) : null;

  const cleanup = useCallback(async () => {
    if (!jobId) return;
    stopPoll();
    try {
      await cleanupVideoDownload(apiBase, jobId);
      setJobId(null);
      setStatus(null);
    } catch (e) {
      setError(e instanceof VideoDownloadApiException ? e.message : String(e));
    }
  }, [apiBase, jobId]);

  return {
    url,
    setUrl,
    quality,
    setQuality,
    status,
    error,
    jobId,
    fileHref,
    enqueue,
    cleanup,
    stopPoll,
  };
}
