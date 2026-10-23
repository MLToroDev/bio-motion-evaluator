import { useEffect, useState } from 'react';
import { persistApiBase, persistTargetRepGoal, readApiBase, readTargetRepGoal } from '../../../lib/prefs';

export function useConnectionConfig() {
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
    alert('Guardado en localStorage.');
  };

  return { base, setBase, goal, setGoal, save };
}
