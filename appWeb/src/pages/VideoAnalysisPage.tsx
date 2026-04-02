import { useCallback, useEffect, useMemo, useState } from 'react';
import { AnalysisSummaryDialog } from '../components/AnalysisSummaryDialog';
import { BmButton } from '../components/BmButton';
import { BmInput, BmSelect } from '../components/BmInput';
import { DashboardPanel } from '../components/DashboardPanel';
import { PoseSkeletonCanvas } from '../components/PoseSkeletonCanvas';
import { useVideoAnalysisSession } from '../hooks/useVideoAnalysisSession';
import {
  kneeFlexionMetricSublabelInContext,
  statusForKneeFlexionInContext,
} from '../lib/angleFormatter';
import { persistApiBase, readApiBase, readTargetRepGoal } from '../lib/prefs';
import {
  PREVIEW_FPS_ALLOWED,
  PREVIEW_JPEG_QUALITY_MAX,
  PREVIEW_JPEG_QUALITY_MIN,
  type PreviewFpsAllowed,
} from '../lib/previewStreamConfig';
import type { AnalysisSummary } from '../lib/videoAnalysisAccumulator';
import { buildGoldStandardVideosHttpUrl } from '../lib/wsUri';
import '../App.css';

function parseFps(t: string): { ok: boolean; value: number; error?: string } {
  const s = t.trim();
  if (!s) return { ok: false, value: 10, error: 'Requerido' };
  const n = Number(s);
  if (!Number.isFinite(n) || n < 0.5 || n > 60) {
    return { ok: false, value: n, error: 'Entre 0.5 y 60 FPS' };
  }
  return { ok: true, value: n };
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

  const [apiBase, setApiBase] = useState(() => readApiBase());
  const [targetRepGoal, setTargetRepGoal] = useState<number | null>(null);
  const [videoFilename, setVideoFilename] = useState('');
  const [fpsText, setFpsText] = useState('10');
  const [includePreview, setIncludePreview] = useState(true);
  const [captureOnly, setCaptureOnly] = useState(true);
  const [serverDiagnostics, setServerDiagnostics] = useState(false);
  const [skeletonOnly, setSkeletonOnly] = useState(false);
  const [previewFps, setPreviewFps] = useState<PreviewFpsAllowed>(10);
  const [previewQuality, setPreviewQuality] = useState(84);

  const [videoList, setVideoList] = useState<string[]>([]);
  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);

  const fpsParsed = useMemo(() => parseFps(fpsText), [fpsText]);
  const formValid = fpsParsed.ok && videoFilename.trim().length > 0 && !ui.running;

  const persistApi = useCallback(() => {
    persistApiBase(apiBase);
  }, [apiBase]);

  const refreshVideos = useCallback(async () => {
    setListLoading(true);
    setListError(null);
    persistApi();
    const url = buildGoldStandardVideosHttpUrl(apiBase);
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
      setVideoFilename((prev) => (prev && list.includes(prev) ? prev : list[0] ?? ''));
    } catch (e) {
      setListError(String(e));
      setVideoList([]);
    } finally {
      clearTimeout(tid);
      setListLoading(false);
    }
  }, [apiBase, persistApi]);

  useEffect(() => {
    void refreshVideos();
    setTargetRepGoal(readTargetRepGoal());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!ui.running) return;
    sendPreviewTuning(previewFps, Math.round(previewQuality));
  }, [previewFps, previewQuality, ui.running, sendPreviewTuning]);

  useEffect(() => {
    if (!snack) return;
    const t = setTimeout(() => setSnack(null), 4000);
    return () => clearTimeout(t);
  }, [snack]);

  const onStart = async () => {
    if (!formValid) return;
    resetCsv();
    const err = await start({
      apiBaseUrl: apiBase,
      videoFilename: videoFilename.trim(),
      targetFps: fpsParsed.value,
      includePreview,
      previewFps,
      previewJpegQuality: Math.round(previewQuality),
      captureOnly,
      serverDiagnostics,
    });
    if (err) console.warn(err);
  };

  const progress =
    ui.running && ui.frameIndex >= 0 && ui.totalFrames != null && ui.totalFrames > 0
      ? Math.min(1, (ui.frameIndex + 1) / ui.totalFrames)
      : null;

  const downloadCsv = () => {
    const text = ui.csvText;
    if (text.split('\n').length < 3) return;
    const blob = new Blob([text], { type: 'text/csv;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'bio_motion_frames.csv';
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const ex = ui.exerciseLabel;
  const leftStatus =
    ui.leftDeg != null ? statusForKneeFlexionInContext(ui.leftDeg, true, ex, ui.rightDeg) : 'neutral';
  const rightStatus =
    ui.rightDeg != null ? statusForKneeFlexionInContext(ui.rightDeg, false, ex, ui.leftDeg) : 'neutral';
  const leftSublabel = kneeFlexionMetricSublabelInContext(ui.leftDeg, true, ex, ui.rightDeg);
  const rightSublabel = kneeFlexionMetricSublabelInContext(ui.rightDeg, false, ex, ui.leftDeg);

  return (
    <div className="app">
      {snack && (
        <div
          className="bm-body"
          style={{
            position: 'fixed',
            bottom: 'var(--bm-space-lg)',
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'var(--bm-accent-muted)',
            color: 'var(--bm-accent)',
            padding: 'var(--bm-space-sm) var(--bm-space-md)',
            borderRadius: 'var(--bm-radius-md)',
            border: '1px solid rgba(0, 230, 118, 0.2)',
            zIndex: 900,
          }}
        >
          {snack}
        </div>
      )}
      <AnalysisSummaryDialog summary={summaryOpen} open={summaryOpen != null} onClose={() => setSummaryOpen(null)} />

      <header className="header">
        <h1 className="bm-screen-title">Análisis de video</h1>
        <p className="subtitle">
          Gold standard en servidor · REST + WebSocket <code>/ws/pose-stream</code>
        </p>
      </header>

      <div className="layout">
        <aside className="panel">
          <BmInput
            label="URL base del API"
            value={apiBase}
            onChange={(e) => setApiBase(e.target.value)}
            onBlur={persistApi}
            disabled={ui.running}
            autoComplete="off"
          />

          <div style={{ marginBottom: 'var(--bm-space-sm)' }}>
            <BmButton variant="outline" onClick={() => void refreshVideos()} disabled={ui.running} loading={listLoading}>
              Actualizar lista de vídeos
            </BmButton>
          </div>
          {listError && <p className="error">{listError}</p>}

          <BmSelect
            label="Vídeo (servidor)"
            value={videoFilename}
            onChange={(e) => setVideoFilename(e.target.value)}
            disabled={ui.running || videoList.length === 0}
          >
            {videoList.length === 0 ? (
              <option value="">— sin vídeos —</option>
            ) : (
              videoList.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))
            )}
          </BmSelect>

          <BmInput
            label="Target FPS"
            value={fpsText}
            onChange={(e) => setFpsText(e.target.value)}
            error={fpsParsed.error}
            disabled={ui.running}
          />

          <label className="check">
            <input
              type="checkbox"
              checked={includePreview}
              onChange={(e) => setIncludePreview(e.target.checked)}
              disabled={ui.running}
            />
            Incluir vista previa JPEG
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={captureOnly}
              onChange={(e) => setCaptureOnly(e.target.checked)}
              disabled={ui.running}
            />
            Solo captura (capture_only)
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={serverDiagnostics}
              onChange={(e) => setServerDiagnostics(e.target.checked)}
              disabled={ui.running}
            />
            Diagnósticos servidor
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={skeletonOnly}
              onChange={(e) => setSkeletonOnly(e.target.checked)}
              disabled={ui.running}
            />
            Vista solo esqueleto
          </label>

          <BmSelect
            label="Preview FPS (8 / 10 / 12)"
            value={String(previewFps)}
            onChange={(e) => setPreviewFps(Number(e.target.value) as PreviewFpsAllowed)}
            disabled={!includePreview}
          >
            {PREVIEW_FPS_ALLOWED.map((v) => (
              <option key={v} value={v}>
                {v} FPS
              </option>
            ))}
          </BmSelect>
          <div className="bm-field">
            <label className="bm-field__label" htmlFor="video-analysis-jpeg-quality">
              Calidad JPEG ({Math.round(previewQuality)}) {PREVIEW_JPEG_QUALITY_MIN}–{PREVIEW_JPEG_QUALITY_MAX}
            </label>
            <input
              id="video-analysis-jpeg-quality"
              type="range"
              className="bm-field__input"
              min={PREVIEW_JPEG_QUALITY_MIN}
              max={PREVIEW_JPEG_QUALITY_MAX}
              value={previewQuality}
              onChange={(e) => setPreviewQuality(Number(e.target.value))}
              disabled={!includePreview}
            />
          </div>

          <div className="actions">
            <BmButton variant="primary" disabled={!formValid} onClick={() => void onStart()}>
              Iniciar análisis
            </BmButton>
            <BmButton variant="outline" disabled={!ui.running} onClick={() => stop(false)}>
              Detener
            </BmButton>
            <BmButton variant="outline" onClick={downloadCsv} disabled={ui.csvText.split('\n').length < 3}>
              Descargar CSV
            </BmButton>
          </div>

          {ui.statusError && <p className="error">{ui.statusError}</p>}
        </aside>

        <main className="main">
          <div className="metrics">
            <p className="bm-caption bm-mono" style={{ margin: 0 }}>
              Pipeline (servidor): {ui.serverPipelineTotalMs != null ? `${ui.serverPipelineTotalMs} ms` : '—'}
            </p>
            <p className="bm-caption bm-mono" style={{ margin: 0 }}>
              Frame: {ui.frameIndex >= 0 ? ui.frameIndex + 1 : '—'}
              {ui.totalFrames != null ? ` / ${ui.totalFrames}` : ''}
            </p>
            {ui.qualityFlags.length > 0 && (
              <p className="bm-caption" style={{ margin: 0 }}>
                Calidad: {ui.qualityFlags.join(', ')}
              </p>
            )}
          </div>

          <DashboardPanel
            running={ui.running}
            captureOnly={captureOnly}
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

          {progress != null && (
            <div className="progress-wrap">
              <div className="progress-bar" style={{ width: `${progress * 100}%` }} />
              <span className="progress-label">
                Frame {ui.frameIndex + 1} / {ui.totalFrames}
              </span>
            </div>
          )}

          <div className="preview-stack" style={{ aspectRatio: `${ui.previewAspect}` }}>
            {ui.previewDataUrl && includePreview && !skeletonOnly && (
              <img
                key={ui.previewKey}
                className="preview-img"
                src={ui.previewDataUrl}
                alt="Vista previa del fotograma"
              />
            )}
            <PoseSkeletonCanvas landmarks={ui.landmarks} mirrorHorizontal={false} />
            {!ui.previewDataUrl && !ui.landmarks && (
              <div className="preview-placeholder">
                {ui.running ? 'Esperando fotogramas…' : 'Inicia un análisis para ver la vista previa'}
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
