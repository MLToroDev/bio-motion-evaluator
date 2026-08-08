import { useCallback, useEffect, useState } from 'react';
import { devApiFetch } from '../../../../lib/devLearningApi';

export const DEFAULT_CLASSES = [
  'idle',
  'squat',
  'lunge',
  'curl',
  'running',
  'pushup',
  'plank',
  'jumping_jack',
  'overhead_press',
  'deadlift',
  'mountain_climber',
];

export type JobListItem = {
  id: string;
  status: string;
  sample_count: number | null;
  model_key: string | null;
  accuracy: number | null;
  macro_f1: number | null;
  balanced_accuracy?: number | null;
  oob_score?: number | null;
  oob_score_caveat?: string | null;
  split_strategy?: string | null;
  leakage_risk?: boolean | null;
  unreliable_classes?: string[];
  created_at: string | null;
  completed_at: string | null;
  error_message: string | null;
};

export type JobDetail = {
  id?: string;
  metrics_json?: {
    confusion_matrix?: number[][];
    class_names?: string[];
    f1_per_class?: Record<string, number>;
    balanced_accuracy?: number;
    oob_score?: number;
    oob_score_caveat?: string;
    split_strategy?: string;
    leakage_risk?: boolean;
    unreliable_classes?: string[];
    train_macro_f1?: number;
    overfit_gap_macro_f1?: number;
    n_groups_train?: number;
    n_groups_val?: number;
  };
};

export function useDevTraining() {
  const [classesStr, setClassesStr] = useState(DEFAULT_CLASSES.join(', '));
  const [validationFraction, setValidationFraction] = useState(0.2);
  const [setActive, setSetActive] = useState(false);
  const [pushHf, setPushHf] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [jobDetail, setJobDetail] = useState<JobDetail | null>(null);

  const loadJobs = useCallback(async () => {
    try {
      const res = await devApiFetch('/training/jobs?limit=30');
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setJobs(data.items || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    void loadJobs();
  }, [loadJobs]);

  const pollRunning = useCallback(async () => {
    const running = jobs.filter((j) => j.status === 'pending' || j.status === 'running');
    if (running.length === 0) return;
    await loadJobs();
  }, [jobs, loadJobs]);

  useEffect(() => {
    const id = window.setInterval(() => void pollRunning(), 2500);
    return () => window.clearInterval(id);
  }, [pollRunning]);

  const enqueue = async () => {
    const classes = classesStr
      .split(/[,]+/)
      .map((s) => s.trim().toLowerCase())
      .filter(Boolean);
    if (classes.length === 0) {
      setError('Indica al menos una clase');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await devApiFetch('/training/jobs', {
        method: 'POST',
        body: JSON.stringify({
          classes,
          validation_fraction: validationFraction,
          set_active: setActive,
          push_hf: pushHf,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      await loadJobs();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const loadDetail = async (id: string) => {
    if (expandedId === id) {
      setExpandedId(null);
      setJobDetail(null);
      return;
    }
    setExpandedId(id);
    try {
      const res = await devApiFetch(`/training/jobs/${id}`);
      if (!res.ok) throw new Error(await res.text());
      setJobDetail(await res.json());
    } catch {
      setJobDetail(null);
    }
  };

  return {
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
  };
}
