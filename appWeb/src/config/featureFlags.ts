/**
 * Flags de presentación para entrega MVP (build-time vía Vite).
 * No eliminan rutas ni código; solo controlan navegación y controles visibles.
 */
function envFlag(name: string, defaultWhenDemo = false): boolean {
  const raw = import.meta.env[name];
  if (raw === 'true') return true;
  if (raw === 'false') return false;
  return defaultWhenDemo;
}

const mvpDemoMode = import.meta.env.VITE_MVP_DEMO_MODE === 'true';

export const flags = {
  /** Modo demo jurado: defaults HU-03/04 y UI simplificada. */
  mvpDemoMode,
  /** Herramientas /dev/* en menú e inicio. */
  showDevTools: mvpDemoMode ? envFlag('VITE_MVP_SHOW_DEV', false) : envFlag('VITE_MVP_SHOW_DEV', true),
  /** Login, perfil, historial, descarga remota. */
  showSprint4: mvpDemoMode ? envFlag('VITE_MVP_SHOW_SPRINT4', false) : envFlag('VITE_MVP_SHOW_SPRINT4', true),
  /** Panel PoseSkeleton3D en análisis por video. */
  showVideo3D: mvpDemoMode ? envFlag('VITE_MVP_SHOW_3D', false) : envFlag('VITE_MVP_SHOW_3D', true),
  /** Controles avanzados en ConfigPanel (fuentes alternativas, capture_only, etc.). */
  showAdvancedVideoConfig: mvpDemoMode
    ? envFlag('VITE_MVP_SHOW_ADV_VIDEO', false)
    : envFlag('VITE_MVP_SHOW_ADV_VIDEO', true),
  /** Selector manual de ejercicio en análisis en vivo. */
  showLiveExerciseSelector: mvpDemoMode
    ? envFlag('VITE_MVP_SHOW_LIVE_EXERCISE', false)
    : envFlag('VITE_MVP_SHOW_LIVE_EXERCISE', true),
  /** Objetivo de repeticiones en configuración de conexión. */
  showRepGoalSetting: mvpDemoMode
    ? envFlag('VITE_MVP_SHOW_REP_GOAL', false)
    : envFlag('VITE_MVP_SHOW_REP_GOAL', true),
} as const;

/** Valores iniciales recomendados para análisis por archivo en demo (HU-04). */
export function mvpVideoAnalysisDefaults(): Partial<{
  inputSource: 'file';
  captureOnly: false;
  exerciseMode: 'auto';
  includePreview: true;
  skeletonOnly: false;
}> {
  if (!flags.mvpDemoMode) return {};
  return {
    inputSource: 'file',
    captureOnly: false,
    exerciseMode: 'auto',
    includePreview: true,
    skeletonOnly: false,
  };
}
