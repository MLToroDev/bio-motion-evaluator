import { useEffect, useState } from 'react';
import { flags } from '../config/featureFlags';
import { buildAuthTokenHttpUrl } from '../lib/wsUri';

export type Sprint4Availability = {
  /** Mostrar login, sesiones, perfil y descarga en navegación e inicio. */
  sprint4UiEnabled: boolean;
  checking: boolean;
  unavailableMessage: string | null;
};

/**
 * Si `VITE_MVP_SHOW_SPRINT4` está activo, comprueba que el API exponga auth (PostgreSQL).
 */
export function useSprint4Availability(apiBase: string): Sprint4Availability {
  const [dbOk, setDbOk] = useState<boolean | null>(flags.showSprint4 ? null : false);

  useEffect(() => {
    if (!flags.showSprint4) {
      setDbOk(false);
      return;
    }
    let cancelled = false;
    const ac = new AbortController();
    const tid = window.setTimeout(() => ac.abort(), 6000);

    void (async () => {
      try {
        const res = await fetch(buildAuthTokenHttpUrl(apiBase), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: 'anonymous@local.test' }),
          signal: ac.signal,
        });
        if (cancelled) return;
        setDbOk(res.ok);
      } catch {
        if (!cancelled) setDbOk(false);
      } finally {
        clearTimeout(tid);
      }
    })();

    return () => {
      cancelled = true;
      clearTimeout(tid);
      ac.abort();
    };
  }, [apiBase]);

  const checking = flags.showSprint4 && dbOk === null;
  const sprint4UiEnabled = flags.showSprint4 && dbOk === true;
  const unavailableMessage =
    flags.showSprint4 && dbOk === false
      ? 'Persistencia no disponible en este entorno (PostgreSQL / auth). Las funciones de cuenta y descarga están ocultas.'
      : null;

  return { sprint4UiEnabled, checking, unavailableMessage };
}
