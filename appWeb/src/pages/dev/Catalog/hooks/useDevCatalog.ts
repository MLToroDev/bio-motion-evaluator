import { useCallback, useEffect, useState } from 'react';
import { devApiFetch } from '../../../../lib/devLearningApi';

export type CatalogExercise = {
  id: string;
  display_es?: string;
  description_es?: string;
};

export type CatalogStats = {
  by_label: Record<string, { pending: number; approved: number; rejected: number }>;
  totals: { pending: number; approved: number; rejected: number; all: number };
};

export type CatalogData = {
  exercises: CatalogExercise[];
  stats: CatalogStats | null;
  last_f1_per_class: Record<string, number>;
};

export function useDevCatalog() {
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<CatalogData | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await devApiFetch('/catalog');
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || res.statusText);
      }
      setData(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setData(null);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return { error, data, load };
}
