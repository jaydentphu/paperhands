import { useState } from 'react';
import type { Cohort } from '../../api/types';
import { COHORT_COLOR_VAR, COHORT_NAME } from '../../lib/cohort';
import { fromMicros } from './money';
import type { Series } from './chartData';

const WIDTH = 960;
const HEIGHT = 240;
const STROKE: Record<Cohort, number> = { A: 1.8, B: 1.8, C: 2.2 };

function toPath(points: { micros: number }[], denom: number, halfAbs: number): string {
  return points
    .map((p, i) => {
      const x = (i / denom) * WIDTH;
      const y = HEIGHT / 2 - (p.micros / halfAbs) * (HEIGHT / 2 - 12);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
}

/** Vertical crosshair snapping to the nearest date, one tooltip listing
 * every series' value at that date (dataviz skill: hover layer ships by
 * default, values lead, line-key not a box). */
export function CumulativeChart({ dates, series }: { dates: string[]; series: Series[] }) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const denom = Math.max(dates.length - 1, 1);
  const allMicros = series.flatMap((s) => s.points.map((p) => p.micros));
  const halfAbs = Math.max(...allMicros.map(Math.abs), 100_000);

  const onMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
    setHoverIndex(Math.round(ratio * denom));
  };

  const hoverX = hoverIndex !== null ? (hoverIndex / denom) * 100 : null;

  return (
    <div className="cum-chart">
      <div className="cum-chart__legend">
        <div className="t-h2">Cumulative P&amp;L</div>
        <div className="cum-chart__legend-spacer" />
        {series.map((s) => (
          <div key={s.cohort} className="cum-chart__legend-item">
            <div
              className="cum-chart__legend-swatch"
              style={{ background: COHORT_COLOR_VAR[s.cohort] }}
            />
            {COHORT_NAME[s.cohort]}
          </div>
        ))}
      </div>

      <div className="cum-chart__plot-row">
        <div
          className="cum-chart__plot"
          onPointerMove={onMove}
          onPointerLeave={() => setHoverIndex(null)}
        >
          <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} preserveAspectRatio="none" className="cum-chart__svg">
            {[0, 0.25, 0.5, 0.75, 1].map((f) => (
              <line
                key={f}
                x1={0}
                y1={HEIGHT * f}
                x2={WIDTH}
                y2={HEIGHT * f}
                stroke={f === 0.5 ? 'rgba(255,255,255,.22)' : 'rgba(255,255,255,.14)'}
                strokeDasharray="1 7"
              />
            ))}
            {series.map((s) => (
              <polyline
                key={s.cohort}
                points={toPath(s.points, denom, halfAbs)}
                fill="none"
                stroke={COHORT_COLOR_VAR[s.cohort]}
                strokeWidth={STROKE[s.cohort]}
                strokeLinejoin="round"
              />
            ))}
            {hoverX !== null && (
              <line
                x1={(hoverX / 100) * WIDTH}
                y1={0}
                x2={(hoverX / 100) * WIDTH}
                y2={HEIGHT}
                stroke="rgba(255,255,255,.3)"
              />
            )}
          </svg>

          {hoverIndex !== null && (
            <div className="cum-chart__tooltip" style={{ left: `${hoverX}%` }}>
              <div className="t-label cum-chart__tooltip-date">{dates[hoverIndex]}</div>
              {series.map((s) => (
                <div key={s.cohort} className="cum-chart__tooltip-row">
                  <span
                    className="cum-chart__legend-swatch"
                    style={{ background: COHORT_COLOR_VAR[s.cohort] }}
                  />
                  <span className="t-row num">${fromMicros(s.points[hoverIndex].micros)}</span>
                  <span className="t-label">{COHORT_NAME[s.cohort]}</span>
                </div>
              ))}
            </div>
          )}

          <div className="cum-chart__x-labels">
            {dates.map((d, i) => (
              <span key={d} style={{ opacity: i === 0 || i === dates.length - 1 ? 1 : 0 }}>
                {d}
              </span>
            ))}
          </div>
        </div>
        <div className="cum-chart__y-labels">
          <span>${fromMicros(halfAbs)}</span>
          <span>$0</span>
          <span>-${fromMicros(halfAbs)}</span>
        </div>
      </div>
    </div>
  );
}
