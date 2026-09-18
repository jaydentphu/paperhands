import { useMemo, useState } from 'react';
import { getPositions } from '../../api/client';
import { useFetch } from '../../api/useFetch';
import { SimulatedNote } from '../../components/SimulatedNote';
import { PositionRow } from './PositionRow';
import './positions.css';

type Tab = 'Open' | 'Closed';

function Header({ closed }: { closed: boolean }) {
  return (
    <div className="positions-row positions-row--header">
      <div>Strategy</div>
      <div>Ticker</div>
      <div>Contract</div>
      <div className="num">Opened</div>
      <div className="num">Entry</div>
      <div className="num">Mark</div>
      <div>{closed ? 'Realized P&L' : 'Unreal. P&L'}</div>
      <div className="num">Days</div>
      <div>{closed ? 'Close reason' : 'Status'}</div>
    </div>
  );
}

export function PositionsView() {
  const [tab, setTab] = useState<Tab>('Open');
  const positionsState = useFetch(() => getPositions(), []);
  const closed = tab === 'Closed';

  const rows = useMemo(() => {
    if (positionsState.status !== 'ready') return [];
    return positionsState.data.filter((p) => p.status === (closed ? 'closed' : 'open'));
  }, [positionsState, closed]);

  if (positionsState.status === 'loading') {
    return (
      <div className="view-placeholder">
        <p className="t-body view-placeholder__note">Loading positions…</p>
      </div>
    );
  }

  if (positionsState.status === 'error') {
    return (
      <div className="view-placeholder">
        <h1 className="t-h1">Positions</h1>
        <p className="t-body view-placeholder__note">
          Could not reach the API: {positionsState.error}
        </p>
      </div>
    );
  }

  return (
    <div className="positions-view">
      <div className="positions-view__header">
        <div className="t-h1">Positions</div>
        <div className="positions-tabs">
          {(['Open', 'Closed'] as const).map((t) => (
            <button
              key={t}
              type="button"
              className={t === tab ? 'positions-tabs__tab positions-tabs__tab--active' : 'positions-tabs__tab'}
              onClick={() => setTab(t)}
            >
              {t}
            </button>
          ))}
        </div>
        <div className="positions-view__spacer" />
        <div className="t-label positions-view__note">Simulated fills · 5 trading-day hold</div>
      </div>

      <div className="positions-table">
        <Header closed={closed} />
        {rows.length === 0 ? (
          <div className="t-label positions-table__empty">No {tab.toLowerCase()} positions.</div>
        ) : (
          rows.map((p) => <PositionRow key={p.id} position={p} closed={closed} />)
        )}
      </div>

      <div className="t-label positions-view__footer">Rows shown: {rows.length}</div>
      <SimulatedNote />
    </div>
  );
}
