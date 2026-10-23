import { flags } from '../../config/featureFlags';
import { BmButton } from '../../components/BmButton';
import { BmInput } from '../../components/BmInput';
import { useConnectionConfig } from './hooks/useConnectionConfig';

export default function ConnectionConfig() {
  const { base, setBase, goal, setGoal, save } = useConnectionConfig();

  return (
    <div style={{ maxWidth: 480 }}>
      <h1 className="bm-screen-title">Configuración de conexión</h1>
      <p className="bm-caption" style={{ marginBottom: 'var(--bm-space-md)' }}>
        {flags.showRepGoalSetting
          ? 'URL del API y objetivo de repeticiones (barra de progreso en dashboards).'
          : 'URL del API del servidor de análisis (FastAPI).'}
      </p>
      <BmInput label="URL base del API" value={base} onChange={(e) => setBase(e.target.value)} autoComplete="off" />
      {flags.showRepGoalSetting ? (
        <BmInput
          label="Objetivo de repeticiones"
          hint="Vacío = sin barra de progreso"
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          inputMode="numeric"
        />
      ) : null}
      <BmButton variant="primary" onClick={save}>
        Guardar
      </BmButton>
    </div>
  );
}
