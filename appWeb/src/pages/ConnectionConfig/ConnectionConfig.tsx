import { BmButton } from '../../components/BmButton';
import { BmInput } from '../../components/BmInput';
import { useConnectionConfig } from './hooks/useConnectionConfig';

export default function ConnectionConfig() {
  const { base, setBase, goal, setGoal, devKey, setDevKey, save } = useConnectionConfig();

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
      <BmInput
        label="X-Dev-API-Key (opcional)"
        hint="Solo si el backend tiene DEV_API_KEY para /api/v1/dev/*"
        value={devKey}
        onChange={(e) => setDevKey(e.target.value)}
        autoComplete="off"
      />
      <BmButton variant="primary" onClick={save}>
        Guardar
      </BmButton>
    </div>
  );
}
