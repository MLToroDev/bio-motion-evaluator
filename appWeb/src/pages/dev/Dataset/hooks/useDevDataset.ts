import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { devApiFetch } from '../../../../lib/devLearningApi';

export type SampleRow = {
  id: string;
  label: string;
  label_source: string;
  review_status: string;
  confidence_at_collection: number | null;
  pose_ok: boolean;
  split: string;
  notes: string | null;
  recorded_at: string | null;
};

export function useDevDataset() {
  const [searchParams, setSearchParams] = useSearchParams();
  const labelFilter = searchParams.get('label') || '';
  const statusFilter = searchParams.get('status') || '';
  const [labelDraft, setLabelDraft] = useState(labelFilter);
  const [items, setItems] = useState<SampleRow[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(() => new Set());

  useEffect(() => {
    setLabelDraft(labelFilter);
  }, [labelFilter]);

  const q = useMemo(() => {
    const p = new URLSearchParams();
    if (labelFilter.trim()) p.set('label', labelFilter.trim());
    if (statusFilter.trim()) p.set('review_status', statusFilter.trim());
    p.set('limit', '100');
    return p.toString();
  }, [labelFilter, statusFilter]);

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await devApiFetch(`/samples?${q}`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setItems(data.items || []);
      setTotal(data.total || 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [q]);

  useEffect(() => {
    void load();
  }, [load]);

  const setLabelUrl = (v: string) => {
    setSearchParams((prev) => {
      const n = new URLSearchParams(prev);
      if (v.trim()) n.set('label', v.trim());
      else n.delete('label');
      return n;
    });
  };

  const setStatusUrl = (v: string) => {
    setSearchParams((prev) => {
      const n = new URLSearchParams(prev);
      if (v.trim()) n.set('status', v.trim());
      else n.delete('status');
      return n;
    });
  };

  const patch = async (id: string, body: Record<string, unknown>) => {
    setBusy(true);
    try {
      const res = await devApiFetch(`/samples/${id}`, { method: 'PATCH', body: JSON.stringify(body) });
      if (!res.ok) throw new Error(await res.text());
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const bulkApprove = async () => {
    if (selected.size === 0) return;
    setBusy(true);
    try {
      const res = await devApiFetch('/samples/bulk-approve', {
        method: 'POST',
        body: JSON.stringify({ ids: [...selected] }),
      });
      if (!res.ok) throw new Error(await res.text());
      setSelected(new Set());
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return {
    labelFilter,
    statusFilter,
    labelDraft,
    setLabelDraft,
    items,
    total,
    error,
    busy,
    selected,
    setSelected,
    load,
    setLabelUrl,
    setStatusUrl,
    patch,
    bulkApprove,
  };
}
