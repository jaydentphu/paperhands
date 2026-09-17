import type { Action, Cohort } from '../../api/types';

export const COHORT_NAME: Record<Cohort, string> = {
  A: 'Cash',
  B: 'Screener',
  C: 'Agent',
};

export const COHORT_SUB: Record<Cohort, string> = {
  A: 'Does nothing',
  B: 'Simple rules',
  C: 'AI research',
};

export const COHORT_TAG: Record<Cohort, string> = {
  A: 'CSH',
  B: 'SCR',
  C: 'AGT',
};

export const ACTION_LABEL: Record<Action, string> = {
  long_call: 'Long Call',
  long_put: 'Long Put',
  no_trade: 'No Trade',
};

export function actionColorVar(action: Action): string {
  if (action === 'long_call') return 'var(--gain)';
  if (action === 'long_put') return 'var(--loss)';
  return 'var(--text-dim)';
}
