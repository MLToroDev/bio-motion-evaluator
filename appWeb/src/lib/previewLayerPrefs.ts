import type { VideoPreviewHudSections } from '../components/VideoPreviewOverlays';

const STORAGE_KEY = 'bm-video-analysis-preview-layers';

/** Preferencias de capas del preview en análisis de vídeo (HUD + esqueleto 2D). */
export type VideoAnalysisPreviewLayerToggles = VideoPreviewHudSections & {
  skeletonOverlay?: boolean;
};

export type PreviewLayerToggleState = {
  rate: boolean;
  mode: boolean;
  exercise: boolean;
  tips: boolean;
  quality: boolean;
  skeletonOverlay: boolean;
  objectsOverlay: boolean;
};

export const defaultPreviewLayerState: PreviewLayerToggleState = {
  rate: true,
  mode: true,
  exercise: true,
  tips: true,
  quality: true,
  skeletonOverlay: true,
  objectsOverlay: true,
};

export function loadPreviewLayerState(): PreviewLayerToggleState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...defaultPreviewLayerState };
    const o = JSON.parse(raw) as Record<string, unknown>;
    const b = (k: string, d: boolean) => (typeof o[k] === 'boolean' ? o[k] : d);
    return {
      rate: b('rate', defaultPreviewLayerState.rate),
      mode: b('mode', defaultPreviewLayerState.mode),
      exercise: b('exercise', defaultPreviewLayerState.exercise),
      tips: b('tips', defaultPreviewLayerState.tips),
      quality: b('quality', defaultPreviewLayerState.quality),
      skeletonOverlay: b('skeletonOverlay', defaultPreviewLayerState.skeletonOverlay),
      objectsOverlay: b('objectsOverlay', defaultPreviewLayerState.objectsOverlay),
    };
  } catch {
    return { ...defaultPreviewLayerState };
  }
}

export function persistPreviewLayerState(next: PreviewLayerToggleState): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    /* noop */
  }
}
