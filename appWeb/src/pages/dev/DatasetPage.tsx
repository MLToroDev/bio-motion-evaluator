import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { BmButton } from '../../components/BmButton';
import { BmInput, BmSelect } from '../../components/BmInput';
import { devApiFetch } from '../../lib/devLearningApi';
import './devPages.css';

type SampleRow = {
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

export default function DatasetPage() {
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

  return (
    <div className="bm-dev-page bm-dev-page--wide">
      <h1 className="bm-screen-title">Dataset de características</h1>
      <p className="bm-caption" style={{ marginBottom: 'var(--bm-space-md)' }}>
        Muestras 32D — revisión manual antes de entrenar.
      </p>
      {error ? <p className="bm-caption bm-dev-msg--error">{error}</p> : null}
      <div className="bm-dev-toolbar">
        <BmInput
          label="Etiqueta"
          value={labelDraft}
          onChange={(e) => setLabelDraft(e.target.value)}
          onBlur={() => setLabelUrl(labelDraft)}
          autoComplete="off"
        />
        <BmSelect label="Estado" value={statusFilter} onChange={(e) => setStatusUrl(e.target.value)}>
          <option value="">(todos)</option>
          <option value="pending">pending</option>
          <option value="approved">approved</option>
          <option value="rejected">rejected</option>
        </BmSelect>
        <div className="bm-dev-toolbar-actions">
          <BmButton variant="outline" type="button" disabled={busy} onClick={() => void load()}>
            Refrescar
          </BmButton>
          <BmButton variant="primary" type="button" disabled={busy || selected.size === 0} onClick={() => void bulkApprove()}>
            Aprobar seleccionadas ({selected.size})
          </BmButton>
        </div>
      </div>
      <p className="bm-dev-total">Total coincidentes: {total}</p>
      <div className="bm-dev-dataset-grid bm-dev-dataset-head">
        <span />
        <span>ID</span>
        <span>Etiqueta</span>
        <span>Estado</span>
        <span>Origen</span>
        <span>Conf.</span>
        <span>Acciones</span>
      </div>
      {items.map((row) => (
        <div key={row.id} className="bm-dev-dataset-grid bm-dev-dataset-row">
          <input
            type="checkbox"
            checked={selected.has(row.id)}
            onChange={(e) => {
              const n = new Set(selected);
              if (e.target.checked) n.add(row.id);
              else n.delete(row.id);
              setSelected(n);
            }}
          />
          <span className="bm-mono" style={{ color: 'var(--bm-text-secondary)' }} title={row.id}>
            {row.id.slice(0, 8)}…
          </span>
          <span>{row.label}</span>
          <span>{row.review_status}</span>
          <span>{row.label_source}</span>
          <span>{row.confidence_at_collection != null ? row.confidence_at_collection.toFixed(2) : '—'}</span>
          <span style={{ display: 'flex', gap: 'var(--bm-space-xs)', flexWrap: 'wrap' }}>
            <BmButton variant="outline" type="button" disabled={busy} onClick={() => void patch(row.id, { review_status: 'approved' })}>
              OK
            </BmButton>
            <BmButton variant="ghost" type="button" disabled={busy} onClick={() => void patch(row.id, { review_status: 'rejected' })}>
              Rechazar
            </BmButton>
          </span>
        </div>
      ))}
    </div>
  );
}
