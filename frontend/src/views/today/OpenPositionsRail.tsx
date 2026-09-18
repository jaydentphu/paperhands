import type { PositionOut } from '../../api/types';
import { COHORT_TAG } from '../../lib/cohort';

function pnlClass(value: string | null): string {
  if (value === null) return '';
  return value.startsWith('-') ? 'open-rail__pnl--loss' : 'open-rail__pnl--gain';
}

/** Sticky right-rail summary of every currently open paper position, across
 * tickers and cohorts. Unrealized P&L comes from the latest daily `Mark`
 * (see NOTES.md) - null until the next mark job runs for a same-day fill. */
export function OpenPositionsRail({ positions }: { positions: PositionOut[] }) {
  return (
    <div className="open-rail">
      <div className="open-rail__header">
        <div className="t-h2">Open positions</div>
        <div className="t-label num">{positions.length} simulated</div>
      </div>

      {positions.length === 0 ? (
        <div className="t-label open-rail__empty">No open positions.</div>
      ) : (
        <div className="open-rail__list">
          {positions.map((p) => (
            <div key={p.id} className="open-rail__row">
              <div className="open-rail__tag">{COHORT_TAG[p.cohort]}</div>
              <div className="open-rail__meta">
                <div className="t-row" title={p.contract_id}>
                  {p.ticker}
                </div>
                <div className="t-label open-rail__sub">
                  Opened {new Date(p.opened_at).toLocaleDateString()}
                </div>
              </div>
              {p.unrealized_pnl !== null ? (
                <div className={`t-row num ${pnlClass(p.unrealized_pnl)}`}>
                  ${p.unrealized_pnl}
                </div>
              ) : (
                <div className="t-row num">${p.open_price}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
