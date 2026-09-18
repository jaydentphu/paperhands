import type { Cohort, MetricsOut, PositionOut } from '../../api/types';
import { toMicros } from './money';

export interface SeriesPoint {
  date: string;
  micros: number;
}

export interface Series {
  cohort: Cohort;
  points: SeriesPoint[];
}

function dateOnly(iso: string): string {
  return iso.slice(0, 10);
}

/** Cumulative realized P&L per cohort, stepped across the shared date axis
 * of every window boundary plus every date a position actually closed on -
 * built from /positions (which now carries realized_pnl, see NOTES.md), not
 * a dedicated time-series endpoint that doesn't exist. */
export function buildSeries(
  metrics: MetricsOut[],
  closedPositions: PositionOut[],
): { dates: string[]; series: Series[] } {
  const windowStart = metrics[0]?.start ?? dateOnly(new Date().toISOString());
  const windowEnd = metrics[0]?.end ?? windowStart;

  const dateSet = new Set([windowStart, windowEnd]);
  for (const p of closedPositions) {
    if (p.closed_at !== null) dateSet.add(dateOnly(p.closed_at));
  }
  const dates = [...dateSet].sort();

  const byCohortAndDate = new Map<string, number>();
  for (const p of closedPositions) {
    if (p.closed_at === null || p.realized_pnl === null) continue;
    const key = `${p.cohort}:${dateOnly(p.closed_at)}`;
    byCohortAndDate.set(key, (byCohortAndDate.get(key) ?? 0) + toMicros(p.realized_pnl));
  }

  const series: Series[] = metrics.map((m) => {
    let running = 0;
    const points = dates.map((date) => {
      running += byCohortAndDate.get(`${m.cohort}:${date}`) ?? 0;
      return { date, micros: running };
    });
    return { cohort: m.cohort, points };
  });

  return { dates, series };
}
