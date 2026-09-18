import { useMemo, useState } from 'react';
import { getDecisions, getPositions } from '../../api/client';
import type { DecisionOut } from '../../api/types';
import { useFetch } from '../../api/useFetch';
import { SimulatedNote } from '../../components/SimulatedNote';
import { OpenPositionsRail } from './OpenPositionsRail';
import './today.css';
import { TickerCard } from './TickerCard';
import { TickerDots } from './TickerDots';

function groupByTicker(decisions: DecisionOut[]): Map<string, DecisionOut[]> {
  const grouped = new Map<string, DecisionOut[]>();
  for (const decision of decisions) {
    const existing = grouped.get(decision.ticker);
    if (existing) {
      existing.push(decision);
    } else {
      grouped.set(decision.ticker, [decision]);
    }
  }
  return grouped;
}

export function TodayView() {
  const decisionsState = useFetch(() => getDecisions(), []);
  const positionsState = useFetch(() => getPositions('open'), []);
  const [selected, setSelected] = useState<string | null>(null);

  const grouped = useMemo<Map<string, DecisionOut[]>>(
    () => (decisionsState.status === 'ready' ? groupByTicker(decisionsState.data) : new Map()),
    [decisionsState],
  );
  const tickers = useMemo(() => [...grouped.keys()].sort(), [grouped]);
  const activeTicker = selected !== null && grouped.has(selected) ? selected : (tickers[0] ?? null);

  if (decisionsState.status === 'loading') {
    return (
      <div className="view-placeholder">
        <p className="t-body view-placeholder__note">Loading today's decisions…</p>
      </div>
    );
  }

  if (decisionsState.status === 'error') {
    return (
      <div className="view-placeholder">
        <h1 className="t-h1">Today</h1>
        <p className="t-body view-placeholder__note">
          Could not reach the API: {decisionsState.error}
        </p>
      </div>
    );
  }

  if (activeTicker === null) {
    return (
      <div className="view-placeholder">
        <h1 className="t-h1">Today</h1>
        <p className="t-body view-placeholder__note">No run has produced decisions yet.</p>
      </div>
    );
  }

  return (
    <div className="today-view">
      <div className="today-view__main">
        <TickerCard ticker={activeTicker} decisions={grouped.get(activeTicker) ?? []} />
        <TickerDots tickers={tickers} selected={activeTicker} onSelect={setSelected} />
      </div>

      <div className="today-view__rail">
        <OpenPositionsRail
          positions={positionsState.status === 'ready' ? positionsState.data : []}
        />
        <SimulatedNote />
      </div>
    </div>
  );
}
