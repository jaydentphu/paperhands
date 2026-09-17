import type { DecisionOut } from '../../api/types';

interface Reasoning {
  thesis: string;
  evidence_for: string[];
  evidence_against: string[];
  invalidation: string;
}

/** `reasoning` is untyped JSON on the wire (src/api/schemas.py declares it
 * `dict[str, Any]`); this is the one shape src/scheduler/cohorts.py ever
 * writes for Cohort C (see NOTES.md). Anything else renders nothing rather
 * than guessing at a layout. */
function asReasoning(value: Record<string, unknown> | null): Reasoning | null {
  if (value === null) return null;
  const { thesis, evidence_for, evidence_against, invalidation } = value;
  if (
    typeof thesis === 'string' &&
    typeof invalidation === 'string' &&
    Array.isArray(evidence_for) &&
    Array.isArray(evidence_against)
  ) {
    return {
      thesis,
      invalidation,
      evidence_for: evidence_for.filter((x): x is string => typeof x === 'string'),
      evidence_against: evidence_against.filter((x): x is string => typeof x === 'string'),
    };
  }
  return null;
}

export function AgentReasoning({ decision }: { decision: DecisionOut }) {
  const reasoning = asReasoning(decision.reasoning);
  if (reasoning === null) return null;

  const confPct = decision.confidence !== null ? Math.round(decision.confidence * 100) : null;

  return (
    <div className="agent-reasoning">
      <div className="agent-reasoning__header">
        <div className="agent-reasoning__orb" aria-hidden="true" />
        <div className="t-h2">Agent reasoning · {decision.ticker}</div>
      </div>

      <div className="agent-reasoning__body">
        <div className="agent-reasoning__main">
          <p className="t-body agent-reasoning__thesis">{reasoning.thesis}</p>

          <div className="agent-reasoning__evidence">
            <div>
              <div className="t-micro agent-reasoning__evidence-label agent-reasoning__evidence-label--for">
                Supports
              </div>
              <ul className="agent-reasoning__list">
                {reasoning.evidence_for.map((item) => (
                  <li key={item} className="t-label agent-reasoning__item">
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <div className="t-micro agent-reasoning__evidence-label agent-reasoning__evidence-label--against">
                Challenges
              </div>
              <ul className="agent-reasoning__list">
                {reasoning.evidence_against.map((item) => (
                  <li key={item} className="t-label agent-reasoning__item">
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="agent-reasoning__invalidation">
            <div className="t-micro">Invalidation</div>
            <div className="t-row">{reasoning.invalidation}</div>
          </div>
        </div>

        {confPct !== null && (
          <div className="agent-reasoning__gauge">
            <div
              className="agent-reasoning__gauge-ring"
              style={{
                background: `conic-gradient(var(--accent) 0% ${confPct}%, rgba(255,255,255,.08) ${confPct}% 100%)`,
              }}
            >
              <div className="agent-reasoning__gauge-inner">
                <div className="t-display num">{confPct}%</div>
                <div className="t-micro">Confidence</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
