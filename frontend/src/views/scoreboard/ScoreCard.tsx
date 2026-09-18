import type { MetricsOut } from '../../api/types';
import { COHORT_COLOR_VAR, COHORT_NAME, COHORT_SUB } from '../../lib/cohort';
import { formatPercent } from './money';

function pnlColor(value: string): string {
  if (value === '0' || value === '0.00') return 'var(--text)';
  return value.startsWith('-') ? 'var(--loss)' : 'var(--gain)';
}

/** One cohort's card: total P&L, a 2x3 stat grid, and a hit-rate bar. Direct
 * port of the mockup's scoreCards, but "Turnover" is swapped for
 * "Median P&L" - no backend field tracks trade turnover (see NOTES.md). */
export function ScoreCard({ metrics }: { metrics: MetricsOut }) {
  const stats: [string, string][] = [
    ['Decisions', String(metrics.decisions)],
    ['No-trade', String(metrics.no_trade_count)],
    ['Trades', String(metrics.trades)],
    ['Avg P&L', `$${metrics.mean_pnl}`],
    ['Median P&L', `$${metrics.median_pnl}`],
    ['Max DD', `-$${metrics.max_drawdown}`],
  ];
  const hitPct = formatPercent(metrics.hit_rate);

  return (
    <div className="score-card">
      <div className="score-card__header">
        <div
          className="score-card__icon"
          style={{ background: COHORT_COLOR_VAR[metrics.cohort] }}
        />
        <div className="score-card__name">
          <div className="t-h2">{COHORT_NAME[metrics.cohort]}</div>
          <div className="t-label score-card__sub">{COHORT_SUB[metrics.cohort]}</div>
        </div>
        <div className="score-card__total">
          <div className="t-display num" style={{ color: pnlColor(metrics.total_pnl) }}>
            ${metrics.total_pnl}
          </div>
          <div className="t-micro score-card__total-label">total P&amp;L</div>
        </div>
      </div>

      <div className="score-card__stats">
        {stats.map(([label, value]) => (
          <div key={label} className="score-card__stat">
            <div className="t-micro">{label}</div>
            <div className="t-row num score-card__stat-value">{value}</div>
          </div>
        ))}
      </div>

      <div className="score-card__hit">
        <div className="score-card__hit-row">
          <span className="t-label">Hit rate</span>
          <span className="t-label num">{hitPct}</span>
        </div>
        <div className="score-card__hit-track">
          <div
            className="score-card__hit-fill"
            style={{ width: hitPct, background: COHORT_COLOR_VAR[metrics.cohort] }}
          />
        </div>
      </div>
    </div>
  );
}
