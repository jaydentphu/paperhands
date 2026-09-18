import type { PositionOut } from '../../api/types';
import { COHORT_COLOR_VAR, COHORT_NAME } from '../../lib/cohort';
import { closeReasonLabel, daysHeld, pnlClass } from './format';

export function PositionRow({ position, closed }: { position: PositionOut; closed: boolean }) {
  const mark = closed ? position.close_price : position.mark_price;
  const pnl = closed ? position.realized_pnl : position.unrealized_pnl;

  return (
    <div className="positions-row">
      <div className="positions-row__strategy">
        <div
          className="positions-row__dot"
          style={{ background: COHORT_COLOR_VAR[position.cohort] }}
        />
        <span>{COHORT_NAME[position.cohort]}</span>
      </div>
      <div className="positions-row__ticker">{position.ticker}</div>
      <div className="positions-row__contract" title={position.contract_id}>
        {position.contract_id}
      </div>
      <div className="num positions-row__dim">
        {new Date(position.opened_at).toLocaleDateString()}
      </div>
      <div className="num">${position.open_price}</div>
      <div className="num">{mark !== null ? `$${mark}` : '—'}</div>
      <div className="positions-row__pnl-cell">
        {pnl !== null ? (
          <span className={`positions-row__pnl ${pnlClass(pnl)}`}>${pnl}</span>
        ) : (
          <span className="positions-row__dim">—</span>
        )}
      </div>
      <div className="num positions-row__dim">{daysHeld(position)}d</div>
      <div className="positions-row__dim">
        {closed ? closeReasonLabel(position.close_reason) : 'Open'}
      </div>
    </div>
  );
}
