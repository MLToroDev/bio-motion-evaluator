import { useEffect, useState } from 'react';
import { persistApiBase, persistTargetRepGoal, readApiBase, readTargetRepGoal } from '../lib/prefs';

export default function ConnectionConfigPage() {
  const [base, setBase] = useState('');
  const [goal, setGoal] = useState('');

  useEffect(() => {
    setBase(readApiBase());
    const g = readTargetRepGoal();
    setGoal(g != null ? String(g) : '');
  }, []);

  const save = () => {
    persistApiBase(base);
    const n = parseInt(goal, 10);
    persistTargetRepGoal(Number.isFinite(n) && n > 0 ? n : null);
    alert('Guardado en localStorage (mismas claves que Flutter).');
  };

  return (
    <div style={{ maxWidth: 480 }}>
      <h1 className="bm-screen-title">Configuración de conexión</h1>
      <p className="bm-caption" style={{ marginBottom: 16 }}>
        URL del API y objetivo de repeticiones (barra de progreso en dashboards).
      </p>
      <label className="field" style={{ display: 'block', marginBottom: 12 }}>
        <span>URL base del API</span>
        <input
          value={base}
          onChange={(e) => setBase(e.target.value)}
          style={{ width: '100%', padding: 8, marginTop: 4, borderRadius: 8, border: '1px solid var(--bm-border)', background: 'var(--bm-surface)', color: 'inherit' }}
        />
      </label>
      <label className="field" style={{ display: 'block', marginBottom: 16 }}>
        <span>Objetivo de repeticiones (vacío = sin barra)</span>
        <input
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          inputMode="numeric"
          style={{ width: '100%', padding: 8, marginTop: 4, borderRadius: 8, border: '1px solid var(--bm-border)', background: 'var(--bm-surface)', color: 'inherit' }}
        />
      </label>
      <button type="button" className="primary" onClick={save}>
        Guardar
      </button>
    </div>
  );
}
