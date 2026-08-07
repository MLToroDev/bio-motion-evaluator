import { useEffect, useState } from 'react';
import { devApiFetch } from '../../../../lib/devLearningApi';

export function VideoThumb({ youtubeId, title }: { youtubeId: string; title: string }) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const id = youtubeId?.trim();
    if (!id) {
      setFailed(true);
      return;
    }
    let cancelled = false;
    let objectUrl: string | null = null;
    setFailed(false);
    setBlobUrl(null);
    void (async () => {
      try {
        const res = await devApiFetch(`/ingest/thumb?id=${encodeURIComponent(id)}`);
        if (!res.ok) throw new Error(String(res.status));
        const blob = await res.blob();
        if (cancelled) return;
        const u = URL.createObjectURL(blob);
        objectUrl = u;
        if (cancelled) {
          URL.revokeObjectURL(u);
          return;
        }
        setBlobUrl(u);
      } catch {
        if (!cancelled) setFailed(true);
      }
    })();
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [youtubeId]);

  if (failed || !blobUrl) {
    return (
      <div className="bm-dev-video-card__thumb-placeholder" aria-hidden>
        🎬
      </div>
    );
  }
  return <img src={blobUrl} alt={title} className="bm-dev-video-card__thumb" loading="lazy" />;
}
