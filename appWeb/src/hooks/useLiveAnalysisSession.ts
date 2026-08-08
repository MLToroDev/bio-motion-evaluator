import { useCallback, useEffect, useRef, useState } from 'react';
import { statusForKneeFlexionInContext } from '../lib/angleFormatter';
import {
  parseDeg,
  parseDetectedObjects,
  parseExerciseValidation,
  parseFrameIndex,
  parseKneesMap,
  parseLandmarksJson,
  parseQualityFlags,
  pipelineTotalMs,
  poseWsErrorMessage,
  type DetectedObjectPayload,
  type ExerciseValidationPayload,
  type LandmarkMap,
} from '../lib/poseWsPayload';
import { buildVideoWebSocketUri, normalizeApiBaseUrl } from '../lib/wsUri';

const MAX_SERIES = 30;
/** Máximo de JPEG enviados sin respuesta JSON aún (backpressure). */
const MAX_IN_FLIGHT = 3;
const JPEG_QUALITY = 0.82;
/** Captura JPEG desacoplada del rAF del overlay (~30 intentos/s). */
const CAPTURE_HZ = 30;

export interface LiveAnalysisUiState {
  cameraOn: boolean;
  transmitting: boolean;
  error: string | null;
  knees: Record<string, unknown> | null;
  frameIndex: number;
  exerciseLabel: string;
  exerciseConfidence: number;
  repPhase: string;
  repCount: number;
  qualityFlags: string[];
  leftDeg: number | null;
  rightDeg: number | null;
  leftSeries: number[];
  rightSeries: number[];
  displayRxPerSec: number;
  serverRttMs: number | null;
  serverPipelineTotalMs: number | null;
  /** Slug de equipo (manual o inferido por detecciones). */
  equipmentLabel: string | null;
  detectedObjects: DetectedObjectPayload[];
  /** Validador / teacher (confirm|reject|changed|uncertain); null si el backend no lo envía. */
  exerciseValidation: ExerciseValidationPayload | null;
}

const initialLive = (): Omit<LiveAnalysisUiState, 'cameraOn'> => ({
  transmitting: false,
  error: null,
  knees: null,
  frameIndex: -1,
  exerciseLabel: 'unknown',
  exerciseConfidence: 0,
  repPhase: 'idle',
  repCount: 0,
  qualityFlags: [],
  leftDeg: null,
  rightDeg: null,
  leftSeries: [],
  rightSeries: [],
  displayRxPerSec: 0,
  serverRttMs: null,
  serverPipelineTotalMs: null,
  equipmentLabel: null,
  detectedObjects: [],
  exerciseValidation: null,
});

export function useLiveAnalysisSession(
  apiBase: string,
  captureOnly = true,
  forcedExerciseLabel: string | null = null,
) {
  const [ui, setUi] = useState<LiveAnalysisUiState>(() => ({
    cameraOn: false,
    ...initialLive(),
  }));
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const captureIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const fpsTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const rxCountRef = useRef(0);
  const rttQueueRef = useRef<number[]>([]);
  const blobPendingRef = useRef(false);
  const lastLRef = useRef<number | null>(null);
  const lastRRef = useRef<number | null>(null);
  const [videoContentAspect, setVideoContentAspect] = useState<number | null>(null);
  /** Solo overlay (cámara); lectura imperativa en PoseSkeletonCanvas, sin setState. */
  const overlayLandmarksRef = useRef<LandmarkMap[] | null>(null);
  /** Cajas de objetos; lectura imperativa en DetectedObjectsCanvas. */
  const overlayObjectsRef = useRef<DetectedObjectPayload[] | null>(null);

  const ensureCanvas = () => {
    if (!canvasRef.current) canvasRef.current = document.createElement('canvas');
    return canvasRef.current;
  };

  const stopTimers = useCallback(() => {
    if (captureIntervalRef.current != null) {
      clearInterval(captureIntervalRef.current);
      captureIntervalRef.current = null;
    }
    if (fpsTimerRef.current) {
      clearInterval(fpsTimerRef.current);
      fpsTimerRef.current = null;
    }
    blobPendingRef.current = false;
    rxCountRef.current = 0;
  }, []);

  const syncVideoAspect = useCallback(() => {
    const v = videoRef.current;
    if (!v || v.videoWidth < 2 || v.videoHeight < 2) return;
    setVideoContentAspect(v.videoWidth / v.videoHeight);
  }, []);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    const v = videoRef.current;
    if (v) {
      v.onloadedmetadata = null;
      v.srcObject = null;
    }
    setVideoContentAspect(null);
    setUi((p) => ({ ...p, cameraOn: false }));
  }, []);

  const startCamera = useCallback(async () => {
    setUi((p) => ({ ...p, error: null }));
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      streamRef.current = stream;
      const v = videoRef.current;
      if (v) {
        v.srcObject = stream;
        v.onloadedmetadata = () => syncVideoAspect();
        await v.play();
        syncVideoAspect();
      }
      setUi((p) => ({ ...p, cameraOn: true }));
    } catch (e) {
      setUi((p) => ({
        ...p,
        error: `Cámara: ${e}. Usa https o localhost y concede permisos.`,
        cameraOn: false,
      }));
    }
  }, [syncVideoAspect]);

  const resetStreamState = useCallback(() => {
    stopTimers();
    rttQueueRef.current = [];
    lastLRef.current = null;
    lastRRef.current = null;
    overlayLandmarksRef.current = null;
    overlayObjectsRef.current = null;
    setUi((p) => ({
      ...p,
      ...initialLive(),
      cameraOn: p.cameraOn,
    }));
  }, [stopTimers]);

  const stopTransmit = useCallback(() => {
    const ws = wsRef.current;
    wsRef.current = null;
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      try {
        ws.close();
      } catch {
        /* noop */
      }
    }
    resetStreamState();
  }, [resetStreamState]);

  const sendOneFrame = useCallback(() => {
    const ws = wsRef.current;
    const v = videoRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN || !v || v.readyState < 2) return;
    if (rttQueueRef.current.length >= MAX_IN_FLIGHT || blobPendingRef.current) return;

    const canvas = ensureCanvas();
    const w = v.videoWidth;
    const h = v.videoHeight;
    if (w < 2 || h < 2) return;
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    // JPEG sin espejar: mismas coordenadas que el frame del <video>; el espejo es solo visual (CSS) + overlay (mirrorHorizontal).
    ctx.drawImage(v, 0, 0, w, h);
    blobPendingRef.current = true;
    canvas.toBlob(
      (blob) => {
        blobPendingRef.current = false;
        if (!blob || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
        rttQueueRef.current.push(performance.now());
        wsRef.current.send(blob);
      },
      'image/jpeg',
      JPEG_QUALITY,
    );
  }, []);

  const startTransmit = useCallback(async () => {
    const v = videoRef.current;
    if (!v || !streamRef.current) {
      setUi((p) => ({ ...p, error: 'Conecta la cámara primero.' }));
      return;
    }

    const url = buildVideoWebSocketUri(normalizeApiBaseUrl(apiBase));
    const ws = new WebSocket(url);

    try {
      await new Promise<void>((resolve, reject) => {
        const t = window.setTimeout(() => reject(new Error('timeout conexión')), 8000);
        ws.onopen = () => {
          clearTimeout(t);
          resolve();
        };
        ws.onerror = () => {
          clearTimeout(t);
          reject(new Error('WebSocket'));
        };
      });
    } catch (e) {
      setUi((p) => ({ ...p, error: `No se pudo conectar: ${e}` }));
      try {
        ws.close();
      } catch {
        /* noop */
      }
      return;
    }

    ws.binaryType = 'arraybuffer';
    const init: Record<string, unknown> = { analyze_pose: true, capture_only: captureOnly };
    const forced = (forcedExerciseLabel ?? '').trim().toLowerCase();
    if (forced) init.forced_exercise_label = forced;
    ws.send(JSON.stringify(init));
    wsRef.current = ws;

    setUi((p) => ({
      ...p,
      ...initialLive(),
      cameraOn: p.cameraOn,
      transmitting: true,
      error: null,
    }));
    lastLRef.current = null;
    lastRRef.current = null;
    rttQueueRef.current = [];
    rxCountRef.current = 0;
    stopTimers();

    fpsTimerRef.current = setInterval(() => {
      const n = rxCountRef.current;
      rxCountRef.current = 0;
      setUi((p) => (p.transmitting ? { ...p, displayRxPerSec: n } : p));
    }, 1000);

    captureIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        sendOneFrame();
      }
    }, 1000 / CAPTURE_HZ);

    ws.onmessage = (ev) => {
      if (typeof ev.data !== 'string') return;
      let map: Record<string, unknown>;
      try {
        map = JSON.parse(ev.data) as Record<string, unknown>;
      } catch {
        return;
      }
      const err = poseWsErrorMessage(map);
      if (err != null) {
        setUi((p) => ({ ...p, error: err }));
        stopTransmit();
        return;
      }

      let rtt: number | null = null;
      if (rttQueueRef.current.length > 0) {
        const t0 = rttQueueRef.current.shift()!;
        rtt = Math.round(performance.now() - t0);
      }
      rxCountRef.current++;

      const landmarks = parseLandmarksJson(map.landmarks);
      const knees = parseKneesMap(map.knees);
      const frameIndex = parseFrameIndex(map.frame_index);
      const exerciseLabel = typeof map.exercise_label === 'string' ? map.exercise_label : 'unknown';
      const exerciseConfidence =
        typeof map.exercise_confidence === 'number' ? map.exercise_confidence : 0;
      const repPhase = typeof map.rep_phase === 'string' ? map.rep_phase : 'idle';
      const repCount = typeof map.rep_count === 'number' ? Math.trunc(map.rep_count) : 0;
      const qualityFlags = parseQualityFlags(map.quality_flags);
      const pipeMs = pipelineTotalMs(map);
      const leftDeg = parseDeg(knees?.left_knee_flexion_angle_deg);
      const rightDeg = parseDeg(knees?.right_knee_flexion_angle_deg);
      const detectedObjects = parseDetectedObjects(map.detected_objects);
      const exerciseValidation = parseExerciseValidation(map.exercise_validation);
      const equipmentLabel =
        typeof map.equipment_label === 'string' && map.equipment_label.trim()
          ? map.equipment_label.trim().toLowerCase()
          : null;

      if (landmarks != null) {
        overlayLandmarksRef.current = landmarks;
      }
      overlayObjectsRef.current = detectedObjects;

      setUi((p) => {
        const next: LiveAnalysisUiState = {
          ...p,
          serverRttMs: rtt ?? p.serverRttMs,
          serverPipelineTotalMs: pipeMs ?? p.serverPipelineTotalMs,
          frameIndex,
          exerciseLabel,
          exerciseConfidence,
          repPhase,
          repCount,
          qualityFlags,
          leftDeg,
          rightDeg,
          equipmentLabel,
          detectedObjects,
          exerciseValidation,
        };
        if (knees != null) {
          next.knees = knees;
        }
        if (leftDeg != null) lastLRef.current = leftDeg;
        if (rightDeg != null) lastRRef.current = rightDeg;
        if (lastLRef.current != null && lastRRef.current != null) {
          const ls = [...p.leftSeries, lastLRef.current];
          const rs = [...p.rightSeries, lastRRef.current];
          while (ls.length > MAX_SERIES) ls.shift();
          while (rs.length > MAX_SERIES) rs.shift();
          next.leftSeries = ls;
          next.rightSeries = rs;
        }
        return next;
      });
    };

    ws.onclose = () => {
      if (wsRef.current !== ws) return;
      wsRef.current = null;
      stopTimers();
      rttQueueRef.current = [];
      setUi((p) => ({
        ...p,
        ...initialLive(),
        cameraOn: p.cameraOn,
      }));
    };
  }, [apiBase, captureOnly, forcedExerciseLabel, sendOneFrame, stopTimers, stopTransmit]);

  useEffect(() => {
    return () => {
      const w = wsRef.current;
      wsRef.current = null;
      w?.close();
      stopTimers();
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, [stopTimers]);

  return {
    ui,
    overlayLandmarksRef,
    overlayObjectsRef,
    videoRef,
    videoContentAspect,
    startCamera,
    stopCamera,
    startTransmit,
    stopTransmit,
    statusForLeft: (ex: string) =>
      ui.leftDeg != null
        ? statusForKneeFlexionInContext(ui.leftDeg, true, ex, ui.rightDeg)
        : ('neutral' as const),
    statusForRight: (ex: string) =>
      ui.rightDeg != null
        ? statusForKneeFlexionInContext(ui.rightDeg, false, ex, ui.leftDeg)
        : ('neutral' as const),
  };
}
