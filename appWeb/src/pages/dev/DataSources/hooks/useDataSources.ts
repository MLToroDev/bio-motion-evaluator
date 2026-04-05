import { useState } from 'react';
import { useDevIngest, type IngestJobDetail, type VideoSearchResult } from '../../../../hooks/useDevIngest';
import type { VideoSegment } from '../components/SegmentEditor';

export function useDataSources() {
  const {
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
  } = useDevIngest();

  const [searchQ, setSearchQ] = useState('');
  const [selectedLabel, setSelectedLabel] = useState('squat');
  const [selected, setSelected] = useState<Set<number>>(() => new Set());
  const [maxVideos] = useState(5);
  const [autoApprove, setAutoApprove] = useState(false);
  const [onlyWindowFull, setOnlyWindowFull] = useState(true);
  const [requirePoseOk, setRequirePoseOk] = useState(true);
  const [emitEvery, setEmitEvery] = useState(3);
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);
  const [expandedDetail, setExpandedDetail] = useState<IngestJobDetail | null>(null);
  const [videoSegments, setVideoSegments] = useState<Record<string, VideoSegment[]>>({});
  const [previewVideo, setPreviewVideo] = useState<VideoSearchResult | null>(null);

  const handleSearch = () => {
    const q = searchQ.trim();
    if (!q) return;
    setSelected(new Set());
    void searchYoutube(q, maxVideos + 5);
  };

  const handleSelectAll = () => {
    if (selected.size === searchResults.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(searchResults.map((_, i) => i)));
    }
  };

  const handleIngest = async () => {
    const videos = searchResults.filter((_, i) => selected.has(i));
    if (videos.length === 0) return;

    const videoSegmentsPayload: Record<string, VideoSegment[]> = {};
    for (const v of videos) {
      const segs = videoSegments[v.youtube_id];
      if (segs && segs.length > 0) {
        videoSegmentsPayload[v.youtube_id] = segs;
      }
    }

    const ok = await createIngestJob({
      label: selectedLabel,
      query: searchQ.trim() || selectedLabel,
      max_videos: videos.length,
      auto_approve: autoApprove,
      only_window_full: onlyWindowFull,
      require_pose_ok: requirePoseOk,
      emit_every: emitEvery,
      video_segments: Object.keys(videoSegmentsPayload).length > 0 ? videoSegmentsPayload : undefined,
    });
    if (ok) setSelected(new Set());
  };

  const toggleJobDetail = async (id: string) => {
    if (expandedJobId === id) {
      setExpandedJobId(null);
      setExpandedDetail(null);
    } else {
      setExpandedJobId(id);
      setExpandedDetail(null);
      const detail = await getJobDetail(id);
      setExpandedDetail(detail);
    }
  };

  return {
    searching,
    searchError,
    searchResults,
    jobs,
    jobsError,
    loadJobs,
    creating,
    createError,
    searchQ,
    setSearchQ,
    selectedLabel,
    setSelectedLabel,
    selected,
    setSelected,
    autoApprove,
    setAutoApprove,
    onlyWindowFull,
    setOnlyWindowFull,
    requirePoseOk,
    setRequirePoseOk,
    emitEvery,
    setEmitEvery,
    expandedJobId,
    expandedDetail,
    videoSegments,
    setVideoSegments,
    previewVideo,
    setPreviewVideo,
    handleSearch,
    handleSelectAll,
    handleIngest,
    toggleJobDetail,
  };
}
