import { useEffect, useRef, useState, type MouseEvent } from 'react';
import { BmButton } from '../../../components/BmButton';
import { BmInput, BmSelect } from '../../../components/BmInput';
import '../devPages.css';
import { SamplePreviewModal } from './components/SamplePreviewModal';
import { useDevDataset } from './hooks/useDevDataset';

function fmtVecPreview(preview: number[] | undefined): string {
  if (!preview?.length) return '—';
  return preview.map((x) => Number(x).toFixed(3)).join(', ');
}

export default function Dataset() {
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [rangeFrom, setRangeFrom] = useState('1');
  const [rangeTo, setRangeTo] = useState('50');
  const lastToggleIdx = useRef<number | null>(null);
  const headerCbRef = useRef<HTMLInputElement | null>(null);

  const {
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
  } = useDevDataset();

  const idsOnPage = items.map((r) => r.id);
  const numSelectedOnPage = idsOnPage.filter((id) => selected.has(id)).length;
  const allOnPageSelected = idsOnPage.length > 0 && numSelectedOnPage === idsOnPage.length;

  useEffect(() => {
    const el = headerCbRef.current;
    if (el) {
      el.indeterminate = numSelectedOnPage > 0 && numSelectedOnPage < idsOnPage.length;
    }
  }, [numSelectedOnPage, idsOnPage.length]);

  const selectAllPage = () => setSelected(new Set(idsOnPage));
  const clearPageSelection = () => {
    const n = new Set(selected);
    for (const id of idsOnPage) n.delete(id);
    setSelected(n);
  };

  const applyRowRange = () => {
    const nItems = items.length;
    if (nItems === 0) return;
    let a = parseInt(rangeFrom.replace(/\s/g, ''), 10);
    let b = parseInt((rangeTo || rangeFrom).replace(/\s/g, ''), 10);
    if (Number.isNaN(a)) a = 1;
    if (Number.isNaN(b)) b = a;
    a = Math.max(1, Math.min(nItems, a));
    b = Math.max(1, Math.min(nItems, b));
    if (a > b) [a, b] = [b, a];
    const n = new Set(selected);
    for (let i = a - 1; i <= b - 1; i++) n.add(items[i].id);
    setSelected(n);
    lastToggleIdx.current = b - 1;
  };

  const toggleRowCheckbox = (rowId: string, index: number, e: MouseEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.shiftKey && lastToggleIdx.current !== null && items.length > 0) {
      const from = Math.min(lastToggleIdx.current, index);
      const to = Math.max(lastToggleIdx.current, index);
      const n = new Set(selected);
      for (let i = from; i <= to; i++) n.add(items[i].id);
      setSelected(n);
      lastToggleIdx.current = index;
      return;
    }
    const n = new Set(selected);
    if (n.has(rowId)) n.delete(rowId);
    else n.add(rowId);
    setSelected(n);
    lastToggleIdx.current = index;
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
      <div className="bm-dev-dataset-select-bar" role="group" aria-label="Selección por página (estilo hoja de cálculo)">
        <BmButton type="button" variant="outline" disabled={busy || items.length === 0} onClick={selectAllPage}>
          Todas en página
        </BmButton>
        <BmButton type="button" variant="ghost" disabled={busy || numSelectedOnPage === 0} onClick={clearPageSelection}>
          Quitar página
        </BmButton>
        <span className="bm-dev-dataset-select-bar__sep" aria-hidden>
          |
        </span>
        <label className="bm-dev-dataset-range">
          <span className="bm-caption">Filas</span>
          <input
            className="bm-dev-dataset-range__input"
            type="number"
            min={1}
            max={Math.max(1, items.length)}
            value={rangeFrom}
            onChange={(e) => setRangeFrom(e.target.value)}
            aria-label="Fila desde (1 = primera visible)"
          />
          <span className="bm-caption">–</span>
          <input
            className="bm-dev-dataset-range__input"
            type="number"
            min={1}
            max={Math.max(1, items.length)}
            value={rangeTo}
            onChange={(e) => setRangeTo(e.target.value)}
            aria-label="Fila hasta"
          />
          <BmButton type="button" variant="outline" disabled={busy || items.length === 0} onClick={applyRowRange}>
            Seleccionar rango
          </BmButton>
        </label>
        <span className="bm-caption bm-dev-dataset-select-hint">
          Mayús+clic entre dos casillas extiende la selección como en Excel (solo filas visibles).
        </span>
      </div>
      <div className="bm-dev-dataset-grid bm-dev-dataset-head">
        <span className="bm-dev-dataset-head-cb">
          <input
            ref={headerCbRef}
            type="checkbox"
            disabled={busy || items.length === 0}
            checked={allOnPageSelected}
            onChange={() => {
              if (allOnPageSelected) clearPageSelection();
              else selectAllPage();
            }}
            title="Seleccionar o anular todas las filas de esta página"
            aria-label="Seleccionar todas las filas de la página actual"
          />
        </span>
        <span>ID</span>
        <span>Etiqueta</span>
        <span>Estado</span>
        <span>Origen</span>
        <span>Conf.</span>
        <span>Vector (preview)</span>
        <span>Acciones</span>
      </div>
      {items.map((row, index) => (
        <div key={row.id} className="bm-dev-dataset-grid bm-dev-dataset-row">
          <input
            type="checkbox"
            checked={selected.has(row.id)}
            onChange={() => {}}
            onClick={(e) => toggleRowCheckbox(row.id, index, e)}
            aria-label={`Seleccionar fila ${index + 1}`}
          />
          <span className="bm-mono" style={{ color: 'var(--bm-text-secondary)' }} title={row.id}>
            {row.id.slice(0, 8)}…
          </span>
          <span>{row.label}</span>
          <span>{row.review_status}</span>
          <span>{row.label_source}</span>
          <span>{row.confidence_at_collection != null ? row.confidence_at_collection.toFixed(2) : '—'}</span>
          <span className="bm-mono bm-dev-dataset-vec-preview" title="Primeros componentes; abre Ver para el vector completo">
            {fmtVecPreview(row.feature_vector_preview)}
          </span>
          <span style={{ display: 'flex', gap: 'var(--bm-space-xs)', flexWrap: 'wrap' }}>
            <BmButton variant="outline" type="button" disabled={busy} onClick={() => setPreviewId(row.id)}>
              Ver
            </BmButton>
            <BmButton variant="outline" type="button" disabled={busy} onClick={() => void patch(row.id, { review_status: 'approved' })}>
              OK
            </BmButton>
            <BmButton variant="ghost" type="button" disabled={busy} onClick={() => void patch(row.id, { review_status: 'rejected' })}>
              Rechazar
            </BmButton>
          </span>
        </div>
      ))}
      {previewId ? <SamplePreviewModal sampleId={previewId} onClose={() => setPreviewId(null)} /> : null}
    </div>
  );
}
