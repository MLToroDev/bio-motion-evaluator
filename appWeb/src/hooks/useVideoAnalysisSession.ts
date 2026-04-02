import { useCallback, useEffect, useRef, useState } from 'react';
import { statusForKneeFlexionInContext } from '../lib/angleFormatter';
import type { FrameLogEntry } from '../lib/frameLogEntry';
import { jpegAspectFromBase64 } from '../lib/jpegAspect';
import { worstRom } from '../lib/metricStatus';
import type { MetricStatus } from '../lib/metricStatus';
import { persistApiBase, persistLastSessionSummary } from '../lib/prefs';
import {
  parseDeg,
  parseFrameIndex,
  parseKneesMap,
  parseLandmarksJson,
  parseQualityFlags,
  parseTotalFrames,
  pipelineTotalMs,
  poseWsErrorMessage,
  type LandmarkMap,
} from '../lib/poseWsPayload';
import { sanitizePreviewFps, sanitizePreviewJpegQuality } from '../lib/previewStreamConfig';
import {
  VideoAnalysisAccumulator,
  type AnalysisSummary,
} from '../lib/videoAnalysisAccumulator';
import { buildPoseStreamWebSocketUri } from '../lib/wsUri';

const CSV_HEADER = 'frame,left_knee_flexion_deg,right_knee_flexion_deg,pose_ok\n';
const MAX_SERIES = 30;
const MAX_LOG = 80;
const MAX_SPARK = 5;

function sessionSummaryLine(frameIndex: number, knees: Record<string, unknown> | null): string {
  const l = parseDeg(knees?.left_knee_flexion_angle_deg);
  const r = parseDeg(knees?.right_knee_flexion_angle_deg);
  const fmt = (d: number | null) => (d != null ? `${d.toFixed(1)}°` : '—');
  return `Análisis de video · frame ${frameIndex} · L ${fmt(l)} · R ${fmt(r)}`;
}

export interface VideoAnalysisUiState {
  running: boolean;
  statusError: string | null;
  previewDataUrl: string | null;
  previewKey: number;
  previewAspect: number;
  landmarks: LandmarkMap[] | null;
  knees: Record<string, unknown> | null;
  qualityFlags: string[];
  frameIndex: number;
  totalFrames: number | null;
  leftDeg: number | null;
  rightDeg: number | null;
  exerciseLabel: string;
  exerciseConfidence: number;
  repPhase: string;
  repCount: number;
  serverPipelineTotalMs: number | null;
  displayRxPerSec: number;
  csvText: string;
  framesProcessed: number;
  leftSeries: number[];
  rightSeries: number[];
  logEntries: FrameLogEntry[];
}

const initialUi = (): VideoAnalysisUiState => ({
  running: false,
  statusError: null,
  previewDataUrl: null,
  previewKey: 0,
  previewAspect: 16 / 9,
  landmarks: null,
  knees: null,
  qualityFlags: [],
  frameIndex: -1,
  totalFrames: null,
  leftDeg: null,
  rightDeg: null,
  exerciseLabel: 'unknown',
  exerciseConfidence: 0,
  repPhase: 'idle',
  repCount: 0,
  serverPipelineTotalMs: null,
  displayRxPerSec: 0,
  csvText: CSV_HEADER,
  framesProcessed: 0,
  leftSeries: [],
  rightSeries: [],
  logEntries: [],
});

export interface SessionStartParams {
  apiBaseUrl: string;
  videoFilename: string;
  targetFps: number;
  includePreview: boolean;
  previewFps: number;
  previewJpegQuality: number;
  captureOnly: boolean;
  serverDiagnostics: boolean;
}

async function wsPayloadToText(data: unknown): Promise<string | null> {
  if (typeof data === 'string') return data;
  if (data instanceof Blob) return data.text();
  if (data instanceof ArrayBuffer) return new TextDecoder('utf-8', { fatal: false }).decode(data);
  return null;
}

export interface UseVideoAnalysisSessionOptions {
  onSessionEnded?: (summary: AnalysisSummary | null, naturalCompletion: boolean) => void;
}

export function useVideoAnalysisSession(opts?: UseVideoAnalysisSessionOptions) {
  const onSessionEndedRef = useRef(opts?.onSessionEnded);
  onSessionEndedRef.current = opts?.onSessionEnded;

  const [ui, setUi] = useState<VideoAnalysisUiState>(initialUi);

  const wsRef = useRef<WebSocket | null>(null);
  const connectingRef = useRef(false);
  const ignoreNextDoneRef = useRef(false);
  const chainRef = useRef(Promise.resolve());
  const rxCountRef = useRef(0);
  const fpsTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const previewKeyRef = useRef(0);
  const csvRef = useRef(CSV_HEADER);
  const framesProcessedRef = useRef(0);
  const accRef = useRef(new VideoAnalysisAccumulator());
  const lastLRef = useRef<number | null>(null);
  const lastRRef = useRef<number | null>(null);
  const sparkLRef = useRef<number[]>([]);
  const sparkRRef = useRef<number[]>([]);
  const logEntriesRef = useRef<FrameLogEntry[]>([]);
  const previewSnapshotRef = useRef<string | null>(null);
  const frameIndexRef = useRef(-1);
  const kneesRef = useRef<Record<string, unknown> | null>(null);
  const persistApiRef = useRef('');
  const leftSeriesRef = useRef<number[]>([]);
  const rightSeriesRef = useRef<number[]>([]);

  const pendingRef = useRef<Partial<VideoAnalysisUiState> | null>(null);
  const microRef = useRef(false);

  const scheduleCoalesced = useCallback((patch: Partial<VideoAnalysisUiState>) => {
    pendingRef.current = { ...pendingRef.current, ...patch };
    if (microRef.current) return;
    microRef.current = true;
    queueMicrotask(() => {
      microRef.current = false;
      const p = pendingRef.current;
      pendingRef.current = null;
      if (p) setUi((prev) => ({ ...prev, ...p }));
    });
  }, []);

  const stopFpsTimer = useCallback(() => {
    if (fpsTimerRef.current) {
      clearInterval(fpsTimerRef.current);
      fpsTimerRef.current = null;
    }
    rxCountRef.current = 0;
    setUi((p) => ({ ...p, displayRxPerSec: 0 }));
  }, []);

  const persistSnapshot = useCallback(() => {
    const fi = frameIndexRef.current;
    if (fi < 0) return;
    persistLastSessionSummary(sessionSummaryLine(fi, kneesRef.current));
    persistApiBase(persistApiRef.current);
  }, []);

  const stop = useCallback(
    (naturalCompletion: boolean) => {
      if (!naturalCompletion) ignoreNextDoneRef.current = true;

      persistSnapshot();

      const summary =
        accRef.current.framesProcessed > 0 ? accRef.current.buildSummary() : null;
      accRef.current.reset();

      stopFpsTimer();
      connectingRef.current = false;
      const ws = wsRef.current;
      wsRef.current = null;
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        try {
          ws.close();
        } catch {
          /* noop */
        }
      }

      onSessionEndedRef.current?.(summary, naturalCompletion);

      setUi((prev) => {
        const base = { ...prev, running: false };
        if (naturalCompletion) return base;
        return {
          ...base,
          previewDataUrl: null,
          previewAspect: 16 / 9,
          landmarks: null,
          knees: null,
          qualityFlags: [],
          frameIndex: -1,
          totalFrames: null,
          serverPipelineTotalMs: null,
          exerciseLabel: 'unknown',
          exerciseConfidence: 0,
          repPhase: 'idle',
          repCount: 0,
          leftDeg: null,
          rightDeg: null,
          leftSeries: [],
          rightSeries: [],
          logEntries: [],
        };
      });

      logEntriesRef.current = [];
      sparkLRef.current = [];
      sparkRRef.current = [];
      lastLRef.current = null;
      lastRRef.current = null;
      leftSeriesRef.current = [];
      rightSeriesRef.current = [];
      previewSnapshotRef.current = null;
      frameIndexRef.current = -1;
      kneesRef.current = null;
    },
    [persistSnapshot, stopFpsTimer],
  );

  const processEvent = useCallback(
    async (data: unknown) => {
      const text = await wsPayloadToText(data);
      if (!text) return;

      let map: Record<string, unknown>;
      try {
        map = JSON.parse(text) as Record<string, unknown>;
      } catch {
        return;
      }

      const err = poseWsErrorMessage(map);
      if (err) {
        stopFpsTimer();
        wsRef.current = null;
        setUi((p) => ({
          ...p,
          running: false,
          statusError: err,
        }));
        return;
      }

      if (map.stream_done === true) return;

      const poseOk = map.pose_ok === true;
      const b64 = typeof map.preview_jpeg_base64 === 'string' ? map.preview_jpeg_base64 : null;

      let previewDataUrl: string | null = null;
      let previewAspectPatch: number | undefined;

      if (b64 && b64.length > 0) {
        const asp = jpegAspectFromBase64(b64);
        previewDataUrl = `data:image/jpeg;base64,${b64}`;
        previewKeyRef.current += 1;
        if (asp != null) previewAspectPatch = asp;
        previewSnapshotRef.current = previewDataUrl;
      }

      const landmarks = parseLandmarksJson(map.landmarks);
      const knees = parseKneesMap(map.knees);
      const frameIndex = parseFrameIndex(map.frame_index);
      const totalFrames = parseTotalFrames(map.total_frames);
      const exerciseLabel = typeof map.exercise_label === 'string' ? map.exercise_label : 'unknown';
      const exerciseConfidence =
        typeof map.exercise_confidence === 'number' ? map.exercise_confidence : 0;
      const repPhase = typeof map.rep_phase === 'string' ? map.rep_phase : 'idle';
      const repCount = typeof map.rep_count === 'number' ? Math.trunc(map.rep_count) : 0;
      const qualityFlags = parseQualityFlags(map.quality_flags);
      const pipeMs = pipelineTotalMs(map);

      const leftDeg = parseDeg(knees?.left_knee_flexion_angle_deg);
      const rightDeg = parseDeg(knees?.right_knee_flexion_angle_deg);

      frameIndexRef.current = frameIndex;
      if (knees) kneesRef.current = knees;

      const exLabel = exerciseLabel;
      const bothGoodRom = (l: number, r: number) =>
        statusForKneeFlexionInContext(l, true, exLabel, r) === 'good' &&
        statusForKneeFlexionInContext(r, false, exLabel, l) === 'good';

      accRef.current.addFrame({
        frameIndex,
        leftDeg,
        rightDeg,
        bothGoodRom,
        exerciseLabel: exLabel,
        repCount,
        repPhase,
        qualityFlags,
      });

      if (leftDeg != null) {
        sparkLRef.current.push(leftDeg);
        if (sparkLRef.current.length > MAX_SPARK) sparkLRef.current.shift();
      }
      if (rightDeg != null) {
        sparkRRef.current.push(rightDeg);
        if (sparkRRef.current.length > MAX_SPARK) sparkRRef.current.shift();
      }
      if (leftDeg != null) lastLRef.current = leftDeg;
      if (rightDeg != null) lastRRef.current = rightDeg;

      let leftSeries = [...leftSeriesRef.current];
      let rightSeries = [...rightSeriesRef.current];
      if (lastLRef.current != null && lastRRef.current != null) {
        leftSeries.push(lastLRef.current);
        rightSeries.push(lastRRef.current);
        while (leftSeries.length > MAX_SERIES) leftSeries.shift();
        while (rightSeries.length > MAX_SERIES) rightSeries.shift();
        leftSeriesRef.current = leftSeries;
        rightSeriesRef.current = rightSeries;
      }

      const rowStatus = (): MetricStatus => {
        const sl =
          leftDeg != null
            ? statusForKneeFlexionInContext(leftDeg, true, exLabel, rightDeg)
            : 'neutral';
        const sr =
          rightDeg != null
            ? statusForKneeFlexionInContext(rightDeg, false, exLabel, leftDeg)
            : 'neutral';
        return worstRom(sl, sr);
      };

      const logEntry: FrameLogEntry = {
        frame: frameIndex,
        leftDeg,
        rightDeg,
        status: rowStatus(),
        sparkLeft: [...sparkLRef.current],
        sparkRight: [...sparkRRef.current],
        previewDataUrl: previewSnapshotRef.current,
        landmarks: landmarks ?? null,
      };
      logEntriesRef.current.push(logEntry);
      while (logEntriesRef.current.length > MAX_LOG) logEntriesRef.current.shift();

      csvRef.current += `${frameIndex},${leftDeg ?? ''},${rightDeg ?? ''},${poseOk}\n`;
      framesProcessedRef.current += 1;
      rxCountRef.current += 1;

      const patch: Partial<VideoAnalysisUiState> = {
        frameIndex,
        exerciseLabel,
        exerciseConfidence,
        repPhase,
        repCount,
        serverPipelineTotalMs: pipeMs,
        leftDeg,
        rightDeg,
        csvText: csvRef.current,
        framesProcessed: framesProcessedRef.current,
        leftSeries,
        rightSeries,
        logEntries: [...logEntriesRef.current],
      };

      if (totalFrames != null) patch.totalFrames = totalFrames;
      if (landmarks != null) {
        patch.landmarks = landmarks;
        patch.knees = knees;
        patch.qualityFlags = qualityFlags;
      }

      if (previewDataUrl) {
        patch.previewDataUrl = previewDataUrl;
        patch.previewKey = previewKeyRef.current;
      }
      if (previewAspectPatch != null) patch.previewAspect = previewAspectPatch;

      scheduleCoalesced(patch);
    },
    [scheduleCoalesced, stopFpsTimer],
  );

  const processEventStable = useRef(processEvent);
  processEventStable.current = processEvent;

  const start = useCallback(
    async (params: SessionStartParams): Promise<string | null> => {
      if (wsRef.current || connectingRef.current) return 'Ya hay una sesión activa';
      connectingRef.current = true;

      persistApiRef.current = params.apiBaseUrl.trim();
      csvRef.current = CSV_HEADER;
      framesProcessedRef.current = 0;
      previewKeyRef.current = 0;
      accRef.current.reset();
      logEntriesRef.current = [];
      sparkLRef.current = [];
      sparkRRef.current = [];
      lastLRef.current = null;
      lastRRef.current = null;
      leftSeriesRef.current = [];
      rightSeriesRef.current = [];
      previewSnapshotRef.current = null;
      frameIndexRef.current = -1;
      kneesRef.current = null;
      ignoreNextDoneRef.current = false;

      setUi({
        ...initialUi(),
        running: true,
        statusError: null,
        csvText: CSV_HEADER,
        framesProcessed: 0,
      });

      rxCountRef.current = 0;
      stopFpsTimer();
      fpsTimerRef.current = setInterval(() => {
        const n = rxCountRef.current;
        rxCountRef.current = 0;
        setUi((p) => (p.running ? { ...p, displayRxPerSec: n } : p));
      }, 1000);

      const url = buildPoseStreamWebSocketUri(params.apiBaseUrl);
      const ws = new WebSocket(url);

      return new Promise((resolve) => {
        let openResolved = false;

        const fail = (msg: string) => {
          if (openResolved) return;
          openResolved = true;
          connectingRef.current = false;
          stopFpsTimer();
          wsRef.current = null;
          setUi((p) => ({
            ...p,
            running: false,
            statusError: msg,
          }));
          resolve(msg);
        };

        ws.onopen = () => {
          connectingRef.current = false;
          wsRef.current = ws;
          try {
            ws.send(
              JSON.stringify({
                source: 'file',
                video_filename: params.videoFilename,
                target_fps: params.targetFps,
                include_preview: params.includePreview,
                preview_fps: sanitizePreviewFps(params.previewFps),
                preview_jpeg_quality: sanitizePreviewJpegQuality(params.previewJpegQuality),
                capture_only: params.captureOnly,
                diagnostics: params.serverDiagnostics,
              }),
            );
          } catch (e) {
            fail(`No se pudo enviar config: ${e}`);
            try {
              ws.close();
            } catch {
              /* noop */
            }
            return;
          }
          openResolved = true;
          resolve(null);
        };

        ws.onerror = () => {
          fail('No se pudo conectar (WebSocket)');
        };

        ws.onclose = () => {
          if (ignoreNextDoneRef.current) {
            ignoreNextDoneRef.current = false;
            connectingRef.current = false;
            wsRef.current = null;
            return;
          }
          wsRef.current = null;
          connectingRef.current = false;
          if (!openResolved) {
            fail('Conexión cerrada antes de abrir');
            return;
          }
          persistSnapshot();
          const summary =
            accRef.current.framesProcessed > 0 ? accRef.current.buildSummary() : null;
          accRef.current.reset();
          stopFpsTimer();
          onSessionEndedRef.current?.(summary, true);
          setUi((p) => ({
            ...p,
            running: false,
          }));
        };

        ws.onmessage = (ev) => {
          chainRef.current = chainRef.current
            .then(() => processEventStable.current(ev.data))
            .catch((e) => console.error('WS cadena pose-stream:', e));
        };
      });
    },
    [persistSnapshot, stopFpsTimer],
  );

  const sendPreviewTuning = useCallback((previewFps: number, previewJpegQuality: number) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    try {
      ws.send(
        JSON.stringify({
          preview_fps: sanitizePreviewFps(previewFps),
          preview_jpeg_quality: sanitizePreviewJpegQuality(previewJpegQuality),
        }),
      );
    } catch {
      /* noop */
    }
  }, []);

  const resetCsv = useCallback(() => {
    csvRef.current = CSV_HEADER;
    framesProcessedRef.current = 0;
    setUi((p) => ({ ...p, csvText: CSV_HEADER, framesProcessed: 0 }));
  }, []);

  useEffect(() => {
    return () => {
      ignoreNextDoneRef.current = true;
      stopFpsTimer();
      const w = wsRef.current;
      wsRef.current = null;
      w?.close();
    };
  }, [stopFpsTimer]);

  return { ui, start, stop, sendPreviewTuning, resetCsv };
}
