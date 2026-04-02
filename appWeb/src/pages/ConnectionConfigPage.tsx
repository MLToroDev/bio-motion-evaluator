import { useEffect, useState } from 'react';
import { BmButton } from '../components/BmButton';
import { BmInput } from '../components/BmInput';
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
      <p className="bm-caption" style={{ marginBottom: 'var(--bm-space-md)' }}>
        URL del API y objetivo de repeticiones (barra de progreso en dashboards).
      </p>
      <BmInput label="URL base del API" value={base} onChange={(e) => setBase(e.target.value)} autoComplete="off" />
      <BmInput
        label="Objetivo de repeticiones"
        hint="Vacío = sin barra de progreso"
        value={goal}
        onChange={(e) => setGoal(e.target.value)}
        inputMode="numeric"
      />
      <BmButton variant="primary" onClick={save}>
        Guardar
      </BmButton>
    </div>
  );
}
