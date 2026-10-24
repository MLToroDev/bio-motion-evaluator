import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { flags } from '../config/featureFlags';
import { useSprint4Availability } from '../hooks/useSprint4Availability';
import { readApiBase } from '../lib/prefs';

type GuardKind = 'sprint4';

export function MvpRouteGuard({ kind, children }: { kind: GuardKind; children: React.ReactNode }) {
  const navigate = useNavigate();
  const { sprint4UiEnabled, checking } = useSprint4Availability(readApiBase());

  const allowed = flags.showSprint4 && (checking || sprint4UiEnabled);

  useEffect(() => {
    if (kind === 'sprint4' && checking) return;
    if (!allowed) navigate('/inicio', { replace: true });
  }, [allowed, checking, kind, navigate]);

  if (!allowed) return null;
  return <>{children}</>;
}
