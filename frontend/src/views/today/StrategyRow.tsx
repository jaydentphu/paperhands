import type { DecisionOut } from '../../api/types';
import { ACTION_LABEL, actionColorVar, COHORT_NAME, COHORT_SUB, COHORT_TAG } from './cohort';

/** One cohort's decision for the selected ticker: action pill, contract,
 * confidence (Agent only - Cash/Screener are deterministic), and the
 * validator's verdict. */
export function StrategyRow({ decision }: { decision: DecisionOut }) {
  const color = actionColorVar(decision.action);
  const rejected = decision.validator_status === 'rejected';

  return (
    <div className="strategy-row">
      <div className="strategy-row__top">
        <div className="strategy-row__tag">{COHORT_TAG[decision.cohort]}</div>
        <div className="strategy-row__name">
          <div className="t-row">{COHORT_NAME[decision.cohort]}</div>
          <div className="t-label strategy-row__sub">{COHORT_SUB[decision.cohort]}</div>
        </div>
        <div className="strategy-row__pill" style={{ borderColor: color, color }}>
          {ACTION_LABEL[decision.action]}
        </div>
        <div className="strategy-row__spacer" />
        {decision.confidence !== null ? (
          <div className="t-label num">Confidence {Math.round(decision.confidence * 100)}%</div>
        ) : (
          <div className="t-label strategy-row__rule-based">Rule-based</div>
        )}
      </div>

      {decision.contract_id !== null && (
        <div className="strategy-row__chip" title={decision.contract_id}>
          {decision.contract_id}
        </div>
      )}

      <div className="strategy-row__verdict">
        <div
          className="strategy-row__dot"
          style={{ background: rejected ? 'var(--warn)' : 'var(--gain)' }}
        />
        <div
          className="t-label"
          style={{ color: rejected ? 'var(--warn)' : 'var(--gain)', fontWeight: 550 }}
        >
          {rejected ? 'Rejected' : 'Accepted'}
        </div>
        {decision.rejection_reason !== null && (
          <div className="t-label strategy-row__sub">· {decision.rejection_reason}</div>
        )}
      </div>
    </div>
  );
}
