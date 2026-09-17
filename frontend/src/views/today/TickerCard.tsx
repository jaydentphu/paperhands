import type { DecisionOut } from '../../api/types';
import { AgentReasoning } from './AgentReasoning';
import { StrategyRow } from './StrategyRow';

const COHORT_ORDER = ['A', 'B', 'C'] as const;

/** The selected ticker's three cohort decisions plus, when Cohort C traded
 * or was rejected with a reasoning payload, its thesis/evidence panel.
 * Replaces the mockup's hero card - see NOTES.md for why price/chart/IV
 * rank/ATR/earnings are dropped (no quote data is exposed by the API). */
export function TickerCard({
  ticker,
  decisions,
}: {
  ticker: string;
  decisions: DecisionOut[];
}) {
  const byCohort = new Map(decisions.map((d) => [d.cohort, d]));
  const agentDecision = byCohort.get('C');

  return (
    <div className="ticker-card">
      <div className="ticker-card__header">
        <div className="t-display">{ticker}</div>
        <div className="t-label">Today's proposals</div>
      </div>

      <div className="ticker-card__rows">
        {COHORT_ORDER.map((cohort) => {
          const decision = byCohort.get(cohort);
          return decision ? <StrategyRow key={cohort} decision={decision} /> : null;
        })}
      </div>

      {agentDecision && <AgentReasoning decision={agentDecision} />}
    </div>
  );
}
