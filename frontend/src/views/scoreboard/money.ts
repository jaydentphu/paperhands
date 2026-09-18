/** Exact decimal-string arithmetic for a display-only aggregate (the
 * chart's running total). NUMERIC(12,4) money strings are scaled to
 * ten-thousandths as integers so summing many of them never drifts the way
 * repeated float addition on parsed strings would. Not used for anything
 * authoritative - the backend (src/evaluator) remains the source of truth
 * for every stored P&L figure. */
const SCALE = 10_000;

export function toMicros(value: string): number {
  const negative = value.startsWith('-');
  const unsigned = negative ? value.slice(1) : value;
  const [whole, fraction = ''] = unsigned.split('.');
  const padded = (fraction + '0000').slice(0, 4);
  const micros = Number(whole) * SCALE + Number(padded);
  return negative ? -micros : micros;
}

export function fromMicros(micros: number): string {
  const sign = micros < 0 ? '-' : '';
  const abs = Math.abs(micros);
  const whole = Math.floor(abs / SCALE);
  const cents = Math.round((abs % SCALE) / 100)
    .toString()
    .padStart(2, '0');
  return `${sign}${whole}.${cents}`;
}

export function formatPercent(fraction: string): string {
  return `${(Number(fraction) * 100).toFixed(0)}%`;
}
