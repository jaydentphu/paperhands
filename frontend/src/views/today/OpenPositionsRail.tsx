import type { PositionOut } from '../../api/types';
import { COHORT_TAG } from './cohort';

/** Sticky right-rail summary of every currently open paper position, across
 * tickers and cohorts - matches the mockup's rail, minus a live mark price
 * (no mark endpoint exists yet, see NOTES.md), so this shows entry price
 * and open date instead of unrealized P&L. */
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
                <div className="t-row open-rail__contract" title={p.contract_id}>
                  {p.contract_id}
                </div>
                <div className="t-label open-rail__sub">
                  Opened {new Date(p.opened_at).toLocaleDateString()}
                </div>
              </div>
              <div className="t-row num">${p.open_price}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
