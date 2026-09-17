/**
 * Mirrors src/api/schemas.py exactly. Dates and datetimes travel over the
 * wire as ISO 8601 strings (Pydantic's default JSON encoding) - typed as
 * `string` here, not `Date`; parse at the point of use.
 *
 * Money fields (open_price, max_loss, hit_rate, ...) are `string`, not
 * `number` - the backend deliberately never lets a Decimal pass through
 * float JSON serialization (see src/api/main.py's converters). Do not
 * `Number()` these for display; only for arithmetic you actually need,
 * and prefer doing that arithmetic in the backend instead.
 */

export type Cohort = 'A' | 'B' | 'C';
export type Action = 'long_call' | 'long_put' | 'no_trade';
export type ValidatorStatus = 'accepted' | 'rejected';
export type PositionStatus = 'open' | 'closed';
export type CloseReason = 'horizon' | 'pre_expiry';
export type RunStatus = 'running' | 'completed' | 'failed';
export type LogLevel = 'debug' | 'info' | 'warning' | 'error';

export interface RunOut {
  id: number;
  run_date: string;
  status: RunStatus;
  started_at: string;
  completed_at: string | null;
}

export interface DecisionOut {
  id: number;
  run_id: number;
  cohort: Cohort;
  ticker: string;
  action: Action;
  contract_id: string | null;
  reasoning: Record<string, unknown> | null;
  confidence: number | null;
  validator_status: ValidatorStatus;
  rejection_reason: string | null;
  created_at: string;
}

export interface PositionOut {
  id: number;
  cohort: Cohort;
  decision_id: number;
  contract_id: string;
  expiry: string;
  opened_at: string;
  open_price: string;
  underlying_open: string;
  underlying_close: string | null;
  quantity: number;
  max_loss: string;
  status: PositionStatus;
  closed_at: string | null;
  close_price: string | null;
  close_reason: CloseReason | null;
}

export interface MetricsOut {
  cohort: Cohort;
  start: string;
  end: string;
  decisions: number;
  no_trade_count: number;
  trades: number;
  hit_rate: string;
  mean_pnl: string;
  median_pnl: string;
  total_pnl: string;
  max_drawdown: string;
  pnl_vs_cash: string;
}

export interface LogOut {
  id: number;
  run_id: number;
  level: LogLevel;
  component: string;
  message: string;
  payload: Record<string, unknown> | null;
  created_at: string;
}
