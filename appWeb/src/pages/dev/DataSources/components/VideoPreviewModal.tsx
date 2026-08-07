import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { BmButton } from '../../../../components/BmButton';
import type { VideoSearchResult } from '../../../../hooks/useDevIngest';
import { mmssToSec } from '../helpers';
import { SegmentEditor, type SegmentFormState, type VideoSegment } from './SegmentEditor';

const YT_API_SRC = 'https://www.youtube.com/iframe_api';

declare global {
  interface Window {
    YT?: {
      Player: new (
        el: HTMLElement | string,
        opts: {
          videoId: string;
          playerVars?: Record<string, unknown>;
          events?: {
            onReady?: (e: { target: YTPlayer }) => void;
            onStateChange?: (e: { data: number }) => void;
          };
        },
      ) => YTPlayer;
      PlayerState?: { PLAYING: number };
    };
    onYouTubeIframeAPIReady?: () => void;
  }
}

interface YTPlayer {
  getCurrentTime(): number;
  destroy(): void;
}

interface VideoPreviewModalProps {
  video: VideoSearchResult;
  segments: VideoSegment[];
  onSegmentsChange: (segs: VideoSegment[]) => void;
  onClose: () => void;
}

export function VideoPreviewModal({
  video,
  segments,
  onSegmentsChange,
  onClose,
}: VideoPreviewModalProps) {
  const playerRef = useRef<YTPlayer | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [playerReady, setPlayerReady] = useState(false);
  const [segForm, setSegForm] = useState<SegmentFormState>({ startVal: '0:00', endVal: '' });
  const [segFormError, setSegFormError] = useState('');
  const [confirmWarning, setConfirmWarning] = useState('');

  useEffect(() => {
    const loadApi = () => {
      if (!document.querySelector(`script[src="${YT_API_SRC}"]`)) {
        const tag = document.createElement('script');
        tag.src = YT_API_SRC;
        tag.async = true;
        document.head.appendChild(tag);
      }
    };

    const initPlayer = () => {
      if (!containerRef.current || !window.YT?.Player) return;
      if (playerRef.current) {
        try { playerRef.current.destroy(); } catch { /* noop */ }
        playerRef.current = null;
      }
      playerRef.current = new window.YT.Player(containerRef.current, {
        videoId: video.youtube_id,
        playerVars: {
          rel: 0,
          modestbranding: 1,
          origin: window.location.origin,
        },
        events: {
          onReady: () => setPlayerReady(true),
        },
      });
    };

    if (window.YT?.Player) {
      initPlayer();
    } else {
      const prevCallback = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        prevCallback?.();
        initPlayer();
      };
      loadApi();
    }

    return () => {
      if (playerRef.current) {
        try { playerRef.current.destroy(); } catch { /* noop */ }
        playerRef.current = null;
      }
      setPlayerReady(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [video.youtube_id]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  const captureTime = useCallback(() => {
    try {
      return playerRef.current?.getCurrentTime() ?? 0;
    } catch {
      return 0;
    }
  }, []);

  const handleAdd = (seg: VideoSegment) => {
    onSegmentsChange([...segments, seg].sort((a, b) => a.start_sec - b.start_sec));
    setConfirmWarning('');
  };

  const handleDelete = (idx: number) => {
    onSegmentsChange(segments.filter((_, i) => i !== idx));
  };

  const handleConfirm = () => {
    const startSec = mmssToSec(segForm.startVal);
    const endSec = mmssToSec(segForm.endVal);
    const hasEnd = segForm.endVal.trim() !== '';

    if (hasEnd && !isNaN(startSec) && !isNaN(endSec) && endSec > startSec) {
      const newSegs = [...segments, { start_sec: startSec, end_sec: endSec }].sort(
        (a, b) => a.start_sec - b.start_sec,
      );
      onSegmentsChange(newSegs);
      setSegForm({ startVal: '0:00', endVal: '' });
      setConfirmWarning('');
      onClose();
      return;
    }

    if (hasEnd) {
      setConfirmWarning('El tramo tiene valores inválidos (fin debe ser mayor que inicio). Corrígelo o borra el campo «Fin» para ignorarlo.');
      return;
    }

    setConfirmWarning('');
    onClose();
  };

  return createPortal(
    <div
      className="bm-modal-overlay"
      role="dialog"
      aria-modal
      aria-label={`Preview: ${video.title}`}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bm-modal-dialog">
        <div className="bm-modal-header">
          <span className="bm-modal-header__title" title={video.title}>
            {video.title}
          </span>
          <button type="button" className="bm-modal-close" aria-label="Cerrar" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="bm-modal-iframe-wrap">
          <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
        </div>

        <div className="bm-modal-segments">
          <div className="bm-modal-segments__title">Segmentos a analizar</div>
          <SegmentEditor
            segments={segments}
            formState={segForm}
            onFormChange={(s) => { setSegForm(s); setConfirmWarning(''); setSegFormError(''); }}
            onAdd={handleAdd}
            onDelete={handleDelete}
            onCaptureStart={captureTime}
            onCaptureEnd={captureTime}
            playerReady={playerReady}
            duration={video.duration_s ?? 0}
            addError={segFormError}
            onClearError={() => setSegFormError('')}
          />
          <div className="bm-modal-segments__footer">
            {confirmWarning && (
              <p className="bm-dev-segment-confirm-warn">{confirmWarning}</p>
            )}
            <BmButton type="button" variant="primary" onClick={handleConfirm} style={{ width: '100%' }}>
              Confirmar
            </BmButton>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}

export type { VideoSegment };
