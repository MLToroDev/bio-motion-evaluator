import { useCallback, useEffect, useRef, useState } from 'react';
import { devApiFetch } from '../lib/devLearningApi';

export type VideoSearchResult = {
  title: string;
  url: string;
  youtube_id: string;
  duration_s: number;
  channel: string;
  thumbnail_url: string;
  view_count: number;
};

export type IngestJobItem = {
  id: string;
  status: string;
  exercise_label: string;
  query: string;
  source_type: string;
  max_videos: number;
  auto_approve: boolean;
  videos_processed: number | null;
  samples_inserted: number | null;
  features_extracted: number | null;
  videos_failed: number | null;
  created_at: string | null;
  completed_at: string | null;
  error_message: string | null;
};

export type IngestJobDetail = IngestJobItem & {
  params_json: Record<string, unknown> | null;
  videos_json: VideoSearchResult[] | null;
  metrics_json: {
    frames_read?: number;
    features_extracted?: number;
    samples_inserted?: number;
    videos_processed?: number;
    videos_failed?: number;
    per_video?: Array<Record<string, unknown>>;
  } | null;
};

export function useDevIngest() {
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<VideoSearchResult[]>([]);
  const [jobs, setJobs] = useState<IngestJobItem[]>([]);
  const [jobsError, setJobsError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const searchYoutube = useCallback(async (q: string, limit = 8) => {
    setSearching(true);
    setSearchError(null);
    setSearchResults([]);
    try {
      const res = await devApiFetch(`/ingest/search?q=${encodeURIComponent(q)}&limit=${limit}`);
      if (!res.ok) throw new Error(await res.text());
      setSearchResults(await res.json());
    } catch (e) {
      setSearchError(e instanceof Error ? e.message : String(e));
    } finally {
      setSearching(false);
    }
  }, []);

  const loadJobs = useCallback(async () => {
    try {
      const res = await devApiFetch('/ingest/jobs?limit=50');
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setJobs(data.items || []);
      setJobsError(null);
    } catch (e) {
      setJobsError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  const createIngestJob = useCallback(
    async (params: {
      label: string;
      query: string;
      max_videos: number;
      auto_approve: boolean;
      only_window_full: boolean;
      require_pose_ok: boolean;
      emit_every: number;
    }) => {
      setCreating(true);
      setCreateError(null);
      try {
        const res = await devApiFetch('/ingest/jobs', {
          method: 'POST',
          body: JSON.stringify({
            label: params.label,
            query: params.query,
            source_type: 'youtube_search',
            max_videos: params.max_videos,
            auto_approve: params.auto_approve,
            params: {
              only_window_full: params.only_window_full,
              require_pose_ok: params.require_pose_ok,
              emit_every: params.emit_every,
            },
          }),
        });
        if (!res.ok) throw new Error(await res.text());
        await loadJobs();
        return true;
      } catch (e) {
        setCreateError(e instanceof Error ? e.message : String(e));
        return false;
      } finally {
        setCreating(false);
      }
    },
    [loadJobs],
  );

  const getJobDetail = useCallback(async (id: string): Promise<IngestJobDetail | null> => {
    try {
      const res = await devApiFetch(`/ingest/jobs/${id}`);
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }, []);

  // Poll jobs every 3 s when any is running
  useEffect(() => {
    void loadJobs();
  }, [loadJobs]);

  useEffect(() => {
    const hasRunning = jobs.some((j) => j.status === 'running' || j.status === 'pending');
    if (hasRunning && !pollRef.current) {
      pollRef.current = setInterval(() => void loadJobs(), 3000);
    } else if (!hasRunning && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [jobs, loadJobs]);

  return {
    searching,
    searchError,
    searchResults,
    searchYoutube,
    jobs,
    jobsError,
    loadJobs,
    creating,
    createError,
    createIngestJob,
    getJobDetail,
  };
}
