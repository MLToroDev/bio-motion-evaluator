import { lazy, Suspense, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { BmButton } from '../../../../components/BmButton';
import { devApiFetch } from '../../../../lib/devLearningApi';

const FeatureVectorStickFigure = lazy(() =>
  import('./FeatureVectorStickFigure').then((m) => ({ default: m.FeatureVectorStickFigure })),
);

export type SampleDetail = {
  id: string;
  label: string;
  label_source: string;
  review_status: string;
  feature_vector: number[];
  confidence_at_collection: number | null;
  pose_ok: boolean;
  split: string;
  notes: string | null;
  session_id: string | null;
  source_file: string | null;
  recorded_at: string | null;
};

function fmtPreviewRow(d: SampleDetail): [string, string][] {
  return [
    ['ID', d.id],
    ['Etiqueta', d.label],
    ['Estado revisión', d.review_status],
    ['Origen etiqueta', d.label_source],
    ['Confianza', d.confidence_at_collection != null ? String(d.confidence_at_collection) : '—'],
    ['pose_ok', String(d.pose_ok)],
    ['Split', d.split],
    ['Archivo / título origen', d.source_file ?? '—'],
    ['Notas', d.notes ?? '—'],
    ['Sesión', d.session_id ?? '—'],
    ['Registrado', d.recorded_at ?? '—'],
  ];
}

export function SamplePreviewModal({ sampleId, onClose }: { sampleId: string; onClose: () => void }) {
  const [detail, setDetail] = useState<SampleDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setDetail(null);
    setLoadError(null);
    void (async () => {
      try {
        const res = await devApiFetch(`/samples/${sampleId}`);
        if (!res.ok) throw new Error(await res.text());
        const data = (await res.json()) as SampleDetail;
        if (!cancelled) setDetail(data);
      } catch (e) {
        if (!cancelled) setLoadError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sampleId]);

  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      if (ev.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const vec: number[] = Array.isArray(detail?.feature_vector) ? detail.feature_vector : [];
  const dim = vec.length;

  return createPortal(
    <div className="bm-modal-overlay" role="dialog" aria-modal="true" aria-labelledby="bm-sample-preview-title">
      <div className="bm-modal-dialog bm-dev-sample-preview-dialog">
        <header className="bm-modal-header">
          <h2 id="bm-sample-preview-title" className="bm-modal-title">
            Vista previa de la muestra
          </h2>
          <BmButton type="button" variant="ghost" onClick={onClose}>
            Cerrar
          </BmButton>
        </header>
        <div className="bm-dev-sample-preview-body">
          {loadError ? <p className="bm-caption bm-dev-msg--error">{loadError}</p> : null}
          {!detail && !loadError ? <p className="bm-caption">Cargando…</p> : null}
          {detail ? (
            <>
              <p className="bm-caption" style={{ marginTop: 0 }}>
                Vector de características ({dim} dimensiones): resumen estadístico de una ventana de poses (ver
                motor), no una foto concreta. La figura resume solo las medias de rodilla codificadas en el vector.
              </p>
              <dl className="bm-dev-sample-preview-dl">
                {fmtPreviewRow(detail).map(([k, v]) => (
                  <div key={k} className="bm-dev-sample-preview-dl__row">
                    <dt>{k}</dt>
                    <dd className={k === 'ID' ? 'bm-mono' : undefined} title={v}>
                      {v}
                    </dd>
                  </div>
                ))}
              </dl>
              {dim >= 21 ? (
                <>
                  <div className="bm-label-large" style={{ marginBottom: 'var(--bm-space-sm)' }}>
                    Interpretación gráfica (aprox.)
                  </div>
                  <Suspense
                    fallback={<p className="bm-caption bm-dev-feature-stick-canvas-fallback">Cargando vista 3D…</p>}
                  >
                    <FeatureVectorStickFigure featureVector={vec} />
                  </Suspense>
                </>
              ) : null}
              <div className="bm-label-large" style={{ marginBottom: 'var(--bm-space-sm)' }}>
                Valores del vector
              </div>
              <div className="bm-dev-sample-vec-grid" aria-label="Componentes del vector">
                {vec.map((x: number, i: number) => (
                  <span key={i} className="bm-dev-sample-vec-cell" title={`Índice ${i}`}>
                    <span className="bm-dev-sample-vec-idx">{i}</span>
                    <span className="bm-mono bm-dev-sample-vec-val">{Number(x).toFixed(6)}</span>
                  </span>
                ))}
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>,
    document.body,
  );
}
