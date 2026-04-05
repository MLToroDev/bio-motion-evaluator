import { useCallback, useEffect, useState } from 'react';
import { devApiFetch } from '../../../../lib/devLearningApi';

export type ModelItem = {
  key: string;
  path: string | null;
  classes: string[] | null;
  window_size: number | null;
  created_at: string | null;
  note: string | null;
  is_active: boolean;
};

export function useDevModels() {
  const [active, setActive] = useState<string | null>(null);
  const [items, setItems] = useState<ModelItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await devApiFetch('/models');
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setActive(data.active ?? null);
      setItems(data.items || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const activate = async (key: string) => {
    setBusyKey(key);
    try {
      const res = await devApiFetch(`/models/${encodeURIComponent(key)}/activate`, { method: 'POST', body: '{}' });
      if (!res.ok) throw new Error(await res.text());
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusyKey(null);
    }
  };

  return { active, items, error, busyKey, load, activate };
}
