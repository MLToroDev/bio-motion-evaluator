import { BmButton } from '../../../components/BmButton';
import { BmInput, BmSelect } from '../../../components/BmInput';
import '../devPages.css';
import { useDevDataset } from './hooks/useDevDataset';

export default function Dataset() {
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
