import { BmButton } from '../../../components/BmButton';
import { BmInput } from '../../../components/BmInput';
import '../devPages.css';
import { useDevTraining } from './hooks/useDevTraining';

export default function Training() {
  const {
    classesStr,
    setClassesStr,
    validationFraction,
    setValidationFraction,
    setActive,
    setSetActive,
    pushHf,
    setPushHf,
    busy,
    error,
    jobs,
    expandedId,
    jobDetail,
    loadJobs,
    enqueue,
    loadDetail,
  } = useDevTraining();

  const metrics = jobDetail?.metrics_json;

  return (
    <div className="bm-dev-page">
      <h1 className="bm-screen-title">Entrenamiento (Celery)</h1>
      <p className="bm-caption" style={{ marginBottom: 'var(--bm-space-md)' }}>
        Usa muestras con review <span className="bm-dev-code-inline">approved</span>. Requiere worker Celery y dependencias de
        entrenamiento (sklearn, skl2onnx).
      </p>
      {error ? <p className="bm-caption bm-dev-msg--error">{error}</p> : null}

      <div className="bm-dev-panel">
        <BmInput label="Clases (separadas por coma)" value={classesStr} onChange={(e) => setClassesStr(e.target.value)} autoComplete="off" />
        <div className="bm-field" style={{ marginBottom: 0 }}>
          <label className="bm-field__label" htmlFor="dev-training-val-frac">
            Fracción validación {(validationFraction * 100).toFixed(0)}%
          </label>
          <input
            id="dev-training-val-frac"
            type="range"
            className="bm-dev-range"
            min={0.1}
            max={0.45}
            step={0.05}
            value={validationFraction}
            onChange={(e) => setValidationFraction(Number(e.target.value))}
          />
        </div>
        <label className="bm-dev-check">
          <input type="checkbox" checked={setActive} onChange={(e) => setSetActive(e.target.checked)} />
          Activar modelo al terminar (manifest)
        </label>
        <label className="bm-dev-check">
          <input type="checkbox" checked={pushHf} onChange={(e) => setPushHf(e.target.checked)} />
          Push a Hugging Face (HF_MODEL_REPO_ID + token)
        </label>
        <BmButton variant="primary" type="button" disabled={busy} onClick={() => void enqueue()}>
          Encolar entrenamiento
        </BmButton>
      </div>

      <h2 className="bm-section-title">Historial</h2>
      <BmButton variant="outline" type="button" onClick={() => void loadJobs()} style={{ marginBottom: 'var(--bm-space-sm)' }}>
        Refrescar
      </BmButton>
      <ul className="bm-dev-list-plain">
        {jobs.map((j) => (
          <li key={j.id} className="bm-dev-card">
            <BmButton variant="ghost" type="button" className="bm-dev-job-expand" onClick={() => void loadDetail(j.id)}>
              <strong>{j.id.slice(0, 8)}</strong> · {j.status}
              {j.accuracy != null ? ` · acc ${j.accuracy.toFixed(3)}` : ''}
              {j.macro_f1 != null ? ` · macroF1 ${j.macro_f1.toFixed(3)}` : ''}
              {j.model_key ? ` · ${j.model_key}` : ''}
            </BmButton>
            {j.error_message ? (
              <p className="bm-caption bm-dev-msg--error" style={{ margin: 'var(--bm-space-xs) 0 0' }}>
                {j.error_message}
              </p>
            ) : null}
            {expandedId === j.id && jobDetail?.id === j.id && metrics?.confusion_matrix && metrics.class_names ? (
              <div style={{ marginTop: 'var(--bm-space-sm)', overflow: 'auto' }}>
                <table className="bm-dev-matrix">
                  <thead>
                    <tr>
                      <th />
                      {metrics.class_names.map((c) => (
                        <th key={c}>{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {metrics.confusion_matrix.map((row, i) => (
                      <tr key={i}>
                        <td style={{ fontWeight: 600 }}>{metrics.class_names![i]}</td>
                        {row.map((cell, ji) => (
                          <td
                            key={ji}
                            style={{
                              textAlign: 'center',
                              background: `rgba(74, 222, 128, ${Math.min(0.35, cell * 0.08)})`,
                            }}
                          >
                            {cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
                {metrics.f1_per_class ? (
                  <pre className="bm-mono bm-caption" style={{ marginTop: 'var(--bm-space-sm)', whiteSpace: 'pre-wrap' }}>
                    {JSON.stringify(metrics.f1_per_class, null, 2)}
                  </pre>
                ) : null}
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
