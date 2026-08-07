import { useCallback, useEffect, useMemo, useState } from 'react';
import { useVideoAnalysisSession } from '../../../hooks/useVideoAnalysisSession';
import {
  kneeFlexionMetricSublabelInContext,
  statusForKneeFlexionInContext,
} from '../../../lib/angleFormatter';
import {
  loadPreviewLayerState,
  persistPreviewLayerState,
  type PreviewLayerToggleState,
} from '../../../lib/previewLayerPrefs';
import { persistApiBase, readApiBase, readTargetRepGoal } from '../../../lib/prefs';
import type { AnalysisSummary } from '../../../lib/videoAnalysisAccumulator';
import { buildGoldStandardVideosHttpUrl } from '../../../lib/wsUri';
import { flags, mvpVideoAnalysisDefaults } from '../../../config/featureFlags';
import type { AnalysisInputSource, ConfigValues, VideoExerciseMode } from '../components/ConfigPanel';

const VIDEO_ANALYSIS_CONFIG_OPEN_KEY = 'bm-video-analysis-config-open';

function readVideoAnalysisConfigOpen(): boolean {
  try {
    return localStorage.getItem(VIDEO_ANALYSIS_CONFIG_OPEN_KEY) !== '0';
  } catch {
    return true;
  }
}

export function parseFps(t: string): { ok: boolean; value: number; error?: string } {
  const s = t.trim();
  if (!s) return { ok: false, value: 10, error: 'Requerido' };
  const n = Number(s);
  if (!Number.isFinite(n) || n < 0.5 || n > 60) {
    return { ok: false, value: n, error: 'Entre 0.5 y 60 FPS' };
  }
  return { ok: true, value: n };
}

export function downloadBlob(text: string, filename: string) {
  const blob = new Blob([text], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

export function useVideoAnalysis() {
  const [summaryOpen, setSummaryOpen] = useState<AnalysisSummary | null>(null);
  const [snack, setSnack] = useState<string | null>(null);

  const { ui, start, stop, sendPreviewTuning, resetCsv } = useVideoAnalysisSession({
    onSessionEnded: (s, natural) => {
      if (natural) setSnack('Análisis completado — puedes iniciar otro');
      if (s && s.framesProcessed > 0) setSummaryOpen(s);
    },
  });

  const [config, setConfig] = useState<ConfigValues>(() => ({
    apiBase: readApiBase(),
    videoFilename: '',
    serverCameraDeviceIndex: 0,
    browserCameraDeviceId: '',
    inputSource: 'file',
    fpsText: '10',
    maxThroughput: false,
    includePreview: true,
    captureOnly: false,
    exerciseMode: 'auto' satisfies VideoExerciseMode,
    serverDiagnostics: false,
    streamTuningAuto: true,
    skeletonOnly: false,
    previewFps: 10,
    previewQuality: 84,
    ...mvpVideoAnalysisDefaults(),
  }));

  const handleConfigChange = useCallback(
    <K extends keyof ConfigValues>(key: K, value: ConfigValues[K]) => {
      setConfig((prev) => {
        const next = { ...prev, [key]: value };
        if (key === 'inputSource') {
          const src = value as AnalysisInputSource;
          if (src === 'browser_camera') {
            next.maxThroughput = false;
          }
        }
        return next;
      });
    },
    [],
  );

  const [targetRepGoal, setTargetRepGoal] = useState<number | null>(null);
  const [videoList, setVideoList] = useState<string[]>([]);
  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [configPanelOpen, setConfigPanelOpen] = useState(readVideoAnalysisConfigOpen);
  const [statsModalOpen, setStatsModalOpen] = useState(false);
  const [previewLayers, setPreviewLayers] = useState<PreviewLayerToggleState>(loadPreviewLayerState);

  const togglePreviewLayer = useCallback((key: keyof PreviewLayerToggleState) => {
    setPreviewLayers((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      persistPreviewLayerState(next);
      return next;
    });
  }, []);

  const toggleConfigPanel = useCallback(() => {
    setConfigPanelOpen((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(VIDEO_ANALYSIS_CONFIG_OPEN_KEY, next ? '1' : '0');
      } catch {
        /* noop */
      }
      return next;
    });
  }, []);

  const fpsParsed = useMemo(() => parseFps(config.fpsText), [config.fpsText]);
  const fpsOk =
    config.inputSource === 'browser_camera'
      ? fpsParsed.ok
      : config.maxThroughput || fpsParsed.ok;
  const formValid =
    !ui.running &&
    fpsOk &&
    (config.inputSource !== 'file' || config.videoFilename.trim().length > 0);
  const csvReady = ui.csvText.split('\n').length >= 3;

  const progress =
    ui.running && ui.frameIndex >= 0 && ui.totalFrames != null && ui.totalFrames > 0
      ? Math.min(1, (ui.frameIndex + 1) / ui.totalFrames)
      : null;

  const ex = ui.exerciseLabel;
  const leftStatus =
    ui.leftDeg != null
      ? statusForKneeFlexionInContext(ui.leftDeg, true, ex, ui.rightDeg)
      : 'neutral';
  const rightStatus =
    ui.rightDeg != null
      ? statusForKneeFlexionInContext(ui.rightDeg, false, ex, ui.leftDeg)
      : 'neutral';
  const leftSublabel = kneeFlexionMetricSublabelInContext(ui.leftDeg, true, ex, ui.rightDeg);
  const rightSublabel = kneeFlexionMetricSublabelInContext(ui.rightDeg, false, ex, ui.leftDeg);

  const persistApi = useCallback(() => {
    persistApiBase(config.apiBase);
  }, [config.apiBase]);

  const refreshVideos = useCallback(async () => {
    setListLoading(true);
    setListError(null);
    persistApiBase(config.apiBase);
    const url = buildGoldStandardVideosHttpUrl(config.apiBase);
    const ac = new AbortController();
    const tid = window.setTimeout(() => ac.abort(), 8000);
    try {
      const res = await fetch(url, { signal: ac.signal });
      if (!res.ok) {
        setListError(`HTTP ${res.status}`);
        setVideoList([]);
        return;
      }
      const decoded = (await res.json()) as { filenames?: unknown };
      const raw = decoded.filenames;
      const list: string[] = [];
      if (Array.isArray(raw)) {
        for (const e of raw) {
          if (typeof e === 'string' && e.trim()) list.push(e.trim());
        }
      }
      setVideoList(list);
      setConfig((prev) => ({
        ...prev,
        videoFilename:
          prev.videoFilename && list.includes(prev.videoFilename) ? prev.videoFilename : list[0] ?? '',
      }));
    } catch (e) {
      setListError(String(e));
      setVideoList([]);
    } finally {
      clearTimeout(tid);
      setListLoading(false);
    }
  }, [config.apiBase]);

  const handleStart = useCallback(async () => {
    if (!formValid) return;
    resetCsv();
    const previewQ = Math.round(config.previewQuality);
    const inputSource = flags.mvpDemoMode ? 'file' : config.inputSource;
    const captureOnly = flags.mvpDemoMode ? false : config.captureOnly;
    const targetFps =
      inputSource === 'browser_camera'
        ? fpsParsed.value
        : config.maxThroughput
          ? 30
          : fpsParsed.value;

    const forcedExerciseLabel =
      !captureOnly && config.exerciseMode !== 'auto' ? config.exerciseMode : null;
    let err: string | null = null;
    if (inputSource === 'file') {
      err = await start({
        mode: 'file',
        apiBaseUrl: config.apiBase,
        videoFilename: config.videoFilename.trim(),
        targetFps,
        maxThroughput: config.maxThroughput,
        includePreview: config.includePreview,
        previewFps: config.previewFps,
        previewJpegQuality: previewQ,
        captureOnly,
        serverDiagnostics: config.serverDiagnostics,
        streamTuning: config.streamTuningAuto ? 'auto' : 'off',
        forcedExerciseLabel,
      });
    } else if (inputSource === 'server_camera') {
      err = await start({
        mode: 'server_camera',
        apiBaseUrl: config.apiBase,
        deviceIndex: config.serverCameraDeviceIndex,
        targetFps,
        maxThroughput: config.maxThroughput,
        includePreview: config.includePreview,
        previewFps: config.previewFps,
        previewJpegQuality: previewQ,
        captureOnly,
        serverDiagnostics: config.serverDiagnostics,
        streamTuning: config.streamTuningAuto ? 'auto' : 'off',
        forcedExerciseLabel,
      });
    } else {
      err = await start({
        mode: 'browser_camera',
        apiBaseUrl: config.apiBase,
        browserDeviceId: config.browserCameraDeviceId.trim(),
        targetFps,
        includePreview: config.includePreview,
        previewJpegQuality: previewQ,
        captureOnly,
        forcedExerciseLabel,
      });
    }
    if (err) console.warn(err);
  }, [formValid, resetCsv, start, config, fpsParsed.value]);

  const handleDownloadCsv = useCallback(() => {
    if (!csvReady) return;
    downloadBlob(ui.csvText, 'bio_motion_frames.csv');
  }, [csvReady, ui.csvText]);

  useEffect(() => {
    void refreshVideos();
    setTargetRepGoal(readTargetRepGoal());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!ui.running || config.inputSource === 'browser_camera') return;
    sendPreviewTuning(config.previewFps, Math.round(config.previewQuality));
  }, [
    config.inputSource,
    config.previewFps,
    config.previewQuality,
    ui.running,
    sendPreviewTuning,
  ]);

  useEffect(() => {
    if (!snack) return;
    const t = setTimeout(() => setSnack(null), 4000);
    return () => clearTimeout(t);
  }, [snack]);

  return {
    ui,
    stop,
    config,
    handleConfigChange,
    targetRepGoal,
    videoList,
    listLoading,
    listError,
    configPanelOpen,
    statsModalOpen,
    setStatsModalOpen,
    previewLayers,
    togglePreviewLayer,
    toggleConfigPanel,
    fpsParsed,
    fpsOk,
    formValid,
    csvReady,
    progress,
    ex,
    leftStatus,
    rightStatus,
    leftSublabel,
    rightSublabel,
    persistApi,
    refreshVideos,
    handleStart,
    handleDownloadCsv,
    snack,
    summaryOpen,
    setSummaryOpen,
  };
}
