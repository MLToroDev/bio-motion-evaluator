import { useEffect, useState } from 'react';
import {
  persistApiBase,
  persistDevApiKey,
  persistTargetRepGoal,
  readApiBase,
  readDevApiKey,
  readTargetRepGoal,
} from '../../../lib/prefs';

export function useConnectionConfig() {
  const [base, setBase] = useState('');
  const [goal, setGoal] = useState('');
  const [devKey, setDevKey] = useState('');

  useEffect(() => {
    setBase(readApiBase());
    const g = readTargetRepGoal();
    setGoal(g != null ? String(g) : '');
    setDevKey(readDevApiKey() || '');
  }, []);

  const save = () => {
    persistApiBase(base);
    const n = parseInt(goal, 10);
    persistTargetRepGoal(Number.isFinite(n) && n > 0 ? n : null);
    persistDevApiKey(devKey);
    alert('Guardado en localStorage (mismas claves que Flutter + Dev API key).');
  };

  return { base, setBase, goal, setGoal, devKey, setDevKey, save };
}
