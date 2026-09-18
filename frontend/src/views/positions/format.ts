import type { CloseReason, PositionOut } from '../../api/types';

const CLOSE_REASON_LABEL: Record<CloseReason, string> = {
  horizon: 'Held to horizon',
  pre_expiry: 'Near expiry',
};

export function closeReasonLabel(reason: CloseReason | null): string {
  return reason === null ? '—' : CLOSE_REASON_LABEL[reason];
}

/** Calendar days held, not trading days - the trading-day calendar (holiday
 * list, weekends) only exists in src/config.py and isn't exposed by the
 * API, so this is an honest approximation, not the PRD's 5-trading-day
 * horizon figure (see NOTES.md). */
export function daysHeld(position: PositionOut): number {
  const opened = new Date(position.opened_at).getTime();
  const end = position.closed_at !== null ? new Date(position.closed_at).getTime() : Date.now();
  return Math.max(0, Math.floor((end - opened) / 86_400_000));
}

export function pnlClass(value: string | null): string {
  if (value === null) return '';
  return value.startsWith('-') ? 'positions-pnl--loss' : 'positions-pnl--gain';
}
