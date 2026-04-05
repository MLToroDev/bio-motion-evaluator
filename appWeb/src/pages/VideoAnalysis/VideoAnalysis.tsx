import { Fragment, lazy, Suspense } from 'react';
import { AnalysisSummaryDialog } from '../../components/AnalysisSummaryDialog';
import { DashboardPanel } from '../../components/DashboardPanel';
import { ConfigPanel } from './components/ConfigPanel';
import { PreviewCanvas } from './components/PreviewCanvas';
import { PreviewLayerToolbar } from './components/PreviewLayerToolbar';
import { SnackBar } from './components/SnackBar';
import { VideoAnalysisActions } from './components/VideoAnalysisActions';
import { VideoAnalysisShell } from './components/VideoAnalysisShell';
import { VideoAnalysisStatsModal } from './components/VideoAnalysisStatsModal';
import { useVideoAnalysis } from './hooks/useVideoAnalysis';

const PoseSkeleton3DPanel = lazy(() =>
  import('../../components/pose3d/PoseSkeleton3DPanel').then((m) => ({ default: m.PoseSkeleton3DPanel })),
);

export default function VideoAnalysis() {
  const {
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
  } = useVideoAnalysis();

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
                exercise: previewLayers.exercise && !config.captureOnly,
                tips: previewLayers.tips,
                quality: previewLayers.quality,
              }}
              skeletonOverlay={previewLayers.skeletonOverlay}
              overlayRxPerSec={ui.running ? ui.displayRxPerSec : null}
              overlayQualityFlags={ui.qualityFlags}
              exerciseLabel={ex}
              exerciseConfidence={ui.exerciseConfidence}
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
