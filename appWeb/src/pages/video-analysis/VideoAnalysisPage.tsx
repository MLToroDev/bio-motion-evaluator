/**
 * VideoAnalysisPage — orquestador: estado, derivaciones y composición de subcomponentes.
 * Presentación: VideoAnalysisShell, modal de estadísticas (HUD + progreso), preview hero, Dashboard inferior, etc.
 */

import { Fragment, lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react';

const VIDEO_ANALYSIS_CONFIG_OPEN_KEY = 'bm-video-analysis-config-open';

function readVideoAnalysisConfigOpen(): boolean {
  try {
    return localStorage.getItem(VIDEO_ANALYSIS_CONFIG_OPEN_KEY) !== '0';
  } catch {
    return true;
  }
}
import { AnalysisSummaryDialog } from '../../components/AnalysisSummaryDialog';
import { DashboardPanel } from '../../components/DashboardPanel';
const PoseSkeleton3DPanel = lazy(() =>
  import('../../components/pose3d/PoseSkeleton3DPanel').then((m) => ({ default: m.PoseSkeleton3DPanel })),
);
import { useVideoAnalysisSession } from '../../hooks/useVideoAnalysisSession';
import {
  kneeFlexionMetricSublabelInContext,
  statusForKneeFlexionInContext,
} from '../../lib/angleFormatter';
import {
  loadPreviewLayerState,
  persistPreviewLayerState,
  type PreviewLayerToggleState,
} from '../../lib/previewLayerPrefs';
import { persistApiBase, readApiBase, readTargetRepGoal } from '../../lib/prefs';
import type { AnalysisSummary } from '../../lib/videoAnalysisAccumulator';
import { buildGoldStandardVideosHttpUrl } from '../../lib/wsUri';

import { ConfigPanel, type ConfigValues } from './ConfigPanel';
import { PreviewCanvas } from './PreviewCanvas';
import { PreviewLayerToolbar } from './PreviewLayerToolbar';
import { SnackBar } from './SnackBar';
import { VideoAnalysisActions } from './VideoAnalysisActions';
import { VideoAnalysisShell } from './VideoAnalysisShell';
import { VideoAnalysisStatsModal } from './VideoAnalysisStatsModal';

function parseFps(t: string): { ok: boolean; value: number; error?: string } {
  const s = t.trim();
  if (!s) return { ok: false, value: 10, error: 'Requerido' };
  const n = Number(s);
  if (!Number.isFinite(n) || n < 0.5 || n > 60) {
    return { ok: false, value: n, error: 'Entre 0.5 y 60 FPS' };
  }
  return { ok: true, value: n };
}

function downloadBlob(text: string, filename: string) {
  const blob = new Blob([text], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

export default function VideoAnalysisPage() {
  const [summaryOpen, setSummaryOpen] = useState<AnalysisSummary | null>(null);
  const [snack, setSnack] = useState<string | null>(null);

  const { ui, start, stop, sendPreviewTuning, resetCsv } = useVideoAnalysisSession({
    onSessionEnded: (s, natural) => {
      if (natural) setSnack('Análisis completado — puedes iniciar otro');
      if (s && s.framesProcessed > 0) setSummaryOpen(s);
    },
  });

  const [config, setConfig] = useState<ConfigValues>({
    apiBase: readApiBase(),
    videoFilename: '',
    fpsText: '10',
    maxThroughput: false,
    includePreview: true,
    captureOnly: true,
    serverDiagnostics: false,
    streamTuningAuto: true,
    skeletonOnly: false,
    previewFps: 10,
    previewQuality: 84,
  });

  const handleConfigChange = useCallback(
    <K extends keyof ConfigValues>(key: K, value: ConfigValues[K]) => {
      setConfig((prev) => ({ ...prev, [key]: value }));
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
  const formValid =
    (config.maxThroughput || fpsParsed.ok) &&
    config.videoFilename.trim().length > 0 &&
    !ui.running;
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
    const err = await start({
      apiBaseUrl: config.apiBase,
      videoFilename: config.videoFilename.trim(),
      targetFps: config.maxThroughput ? 30 : fpsParsed.value,
      maxThroughput: config.maxThroughput,
      includePreview: config.includePreview,
      previewFps: config.previewFps,
      previewJpegQuality: Math.round(config.previewQuality),
      captureOnly: config.captureOnly,
      serverDiagnostics: config.serverDiagnostics,
      streamTuning: config.streamTuningAuto ? 'auto' : 'off',
    });
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
    if (!ui.running) return;
    sendPreviewTuning(config.previewFps, Math.round(config.previewQuality));
  }, [config.previewFps, config.previewQuality, ui.running, sendPreviewTuning]);

  useEffect(() => {
    if (!snack) return;
    const t = setTimeout(() => setSnack(null), 4000);
    return () => clearTimeout(t);
  }, [snack]);

  return (
    <VideoAnalysisShell
      configOpen={configPanelOpen}
      onToggleConfig={toggleConfigPanel}
      overlays={
        <Fragment>
          <SnackBar message={snack} />
          <AnalysisSummaryDialog
            summary={summaryOpen}
            open={summaryOpen != null}
            onClose={() => setSummaryOpen(null)}
          />
          <VideoAnalysisStatsModal
            open={statsModalOpen}
            onClose={() => setStatsModalOpen(false)}
            serverPipelineTotalMs={ui.serverPipelineTotalMs}
            frameIndex={ui.frameIndex}
            totalFrames={ui.totalFrames}
            qualityFlags={ui.qualityFlags}
            progress={progress}
          />
        </Fragment>
      }
      sidebar={
        <ConfigPanel
          values={config}
          onChange={handleConfigChange}
          onPersistApi={persistApi}
          onRefreshVideos={() => void refreshVideos()}
          onStart={() => void handleStart()}
          onStop={() => stop(false)}
          onDownloadCsv={handleDownloadCsv}
          videoList={videoList}
          listLoading={listLoading}
          listError={listError}
          fpsParsedError={fpsParsed.error}
          formValid={formValid}
          running={ui.running}
          csvReady={csvReady}
          statusError={ui.statusError}
          onCollapsePanel={toggleConfigPanel}
        />
      }
      mainColumn={
        <Fragment>
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '0.65rem',
            }}
          >
            <PreviewLayerToolbar layers={previewLayers} onToggle={togglePreviewLayer} />
            <button
              type="button"
              onClick={() => setStatsModalOpen(true)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.45rem',
                padding: '0.4rem 0.75rem',
                fontFamily: 'var(--bm-font-body)',
                fontSize: '0.8125rem',
                fontWeight: 600,
                color: 'var(--bm-text-secondary)',
                background: 'var(--bm-surface)',
                border: '1px solid var(--bm-border)',
                borderRadius: 'var(--bm-radius-sm)',
                cursor: 'pointer',
                flexShrink: 0,
                marginLeft: 'auto',
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                <path d="M18 20V10M12 20V4M6 20v-6" strokeLinecap="round" />
              </svg>
              Estadísticas
              {ui.running && ui.frameIndex >= 0 ? (
                <span className="bm-mono" style={{ fontSize: '0.72rem', color: 'var(--bm-accent)' }}>
                  {ui.frameIndex + 1}
                  {ui.totalFrames != null ? `/${ui.totalFrames}` : ''}
                </span>
              ) : null}
            </button>
          </div>
          {!configPanelOpen ? (
            <VideoAnalysisActions
              variant="main-toolbar"
              formValid={formValid}
              running={ui.running}
              csvReady={csvReady}
              onStart={() => void handleStart()}
              onStop={() => stop(false)}
              onDownloadCsv={handleDownloadCsv}
            />
          ) : null}
          <div
            style={{
              flex: '1 1 auto',
              minHeight: 0,
              display: 'flex',
              flexDirection: 'column',
              gap: '0.5rem',
            }}
          >
            <PreviewCanvas
              previewDataUrl={ui.previewDataUrl}
              previewKey={ui.previewKey}
              previewAspect={ui.previewAspect}
              landmarks={ui.landmarks}
              includePreview={config.includePreview}
              skeletonOnly={config.skeletonOnly}
              running={ui.running}
              hudSections={{
                rate: previewLayers.rate,
                mode: previewLayers.mode,
                tips: previewLayers.tips,
                quality: previewLayers.quality,
              }}
              skeletonOverlay={previewLayers.skeletonOverlay}
              overlayRxPerSec={ui.running ? ui.displayRxPerSec : null}
              overlayQualityFlags={ui.qualityFlags}
              variant="hero"
            />
            <Suspense
              fallback={
                <div
                  className="bm-caption"
                  style={{
                    border: '1px solid var(--bm-border)',
                    borderRadius: 'var(--bm-radius-md)',
                    padding: '2rem',
                    textAlign: 'center',
                    color: 'var(--bm-text-secondary)',
                  }}
                >
                  Cargando vista 3D…
                </div>
              }
            >
              <PoseSkeleton3DPanel
                landmarks={ui.landmarks}
                worldLandmarks={ui.worldLandmarks}
                mirrorHorizontal={false}
              />
            </Suspense>
          </div>
          <div
            style={{
              flexShrink: 0,
              marginTop: 'auto',
              paddingTop: '0.5rem',
              borderTop: '1px solid var(--bm-border)',
            }}
          >
            <DashboardPanel
              className="dashboard-panel--dock-bottom"
              running={ui.running}
              captureOnly={config.captureOnly}
              targetRepGoal={targetRepGoal}
              exerciseLabel={ex}
              exerciseConfidence={ui.exerciseConfidence}
              repPhase={ui.repPhase}
              repCount={ui.repCount}
              leftDeg={ui.leftDeg}
              rightDeg={ui.rightDeg}
              leftStatus={leftStatus}
              rightStatus={rightStatus}
              leftSublabel={leftSublabel}
              rightSublabel={rightSublabel}
              displayRxPerSec={ui.displayRxPerSec}
              logEntries={ui.logEntries}
              leftSeries={ui.leftSeries}
              rightSeries={ui.rightSeries}
            />
          </div>
        </Fragment>
      }
    />
  );
}
