/**
 * Catálogo de ejercicios del motor + enriquecimiento UI
 * (dataset externo hasaneyldrm/exercises-dataset vía CDN).
 */

export type ExerciseCatalogEntry = {
  id: string;
  display_es: string;
  rep_tracker_key?: string;
  description_es?: string;
  equipment?: string;
  target_muscle?: string;
  muscle_group?: string;
  gif_url?: string;
  instructions_es?: string;
  external_name?: string;
};

export type ExerciseCatalogResponse = {
  version?: number;
  source_note_es?: string;
  external_dataset?: {
    repo?: string;
    cdn_base?: string;
    attribution?: string;
  };
  exercises: ExerciseCatalogEntry[];
  by_id: Record<string, ExerciseCatalogEntry>;
};

const FALLBACK: ExerciseCatalogResponse = {
  version: 0,
  exercises: [],
  by_id: {},
};

export async function fetchExerciseCatalog(apiBase: string): Promise<ExerciseCatalogResponse> {
  const base = apiBase.replace(/\/$/, '');
  const res = await fetch(`${base}/api/v1/exercises/catalog`);
  if (!res.ok) return FALLBACK;
  const data = (await res.json()) as ExerciseCatalogResponse;
  if (!data.by_id || typeof data.by_id !== 'object') {
    const by_id: Record<string, ExerciseCatalogEntry> = {};
    for (const e of data.exercises || []) {
      if (e?.id) by_id[e.id] = e;
    }
    data.by_id = by_id;
  }
  return data;
}

export function resolveExerciseDisplay(
  label: string,
  catalog: ExerciseCatalogResponse | null,
): { title: string; entry: ExerciseCatalogEntry | null } {
  const id = (label || 'unknown').trim().toLowerCase();
  if (!id || id === 'unknown') {
    return { title: 'Sin detectar', entry: null };
  }
  const entry = catalog?.by_id?.[id] ?? null;
  return { title: entry?.display_es || id, entry };
}
