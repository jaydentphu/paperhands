import { useMemo } from 'react';
import { getMetrics, getPositions } from '../../api/client';
import { useFetch } from '../../api/useFetch';
import { SimulatedNote } from '../../components/SimulatedNote';
import { buildSeries } from './chartData';
import { CumulativeChart } from './CumulativeChart';
import { ScoreCard } from './ScoreCard';
import './scoreboard.css';

export function ScoreboardView() {
  const metricsState = useFetch(() => getMetrics(), []);
  const closedState = useFetch(() => getPositions('closed'), []);

  const chart = useMemo(() => {
    if (metricsState.status !== 'ready' || closedState.status !== 'ready') return null;
    return buildSeries(metricsState.data, closedState.data);
  }, [metricsState, closedState]);

  if (metricsState.status === 'loading') {
    return (
      <div className="view-placeholder">
        <p className="t-body view-placeholder__note">Loading scoreboard…</p>
      </div>
    );
  }

  if (metricsState.status === 'error') {
    return (
      <div className="view-placeholder">
        <h1 className="t-h1">Scoreboard</h1>
        <p className="t-body view-placeholder__note">
          Could not reach the API: {metricsState.error}
        </p>
      </div>
    );
  }

  if (metricsState.data.length === 0) {
    return (
      <div className="view-placeholder">
        <h1 className="t-h1">Scoreboard</h1>
        <p className="t-body view-placeholder__note">No runs yet.</p>
      </div>
    );
  }

  const { start, end } = metricsState.data[0];

  return (
    <div className="scoreboard-view">
      <div className="scoreboard-view__header">
        <div className="t-h1">Scoreboard</div>
        <div className="t-label scoreboard-view__range">
          {start} – {end}
        </div>
        <div className="scoreboard-view__spacer" />
        <div className="pill">Simulated results, conservative fills</div>
      </div>

      <div className="scoreboard-view__cards">
        {metricsState.data.map((m) => (
          <ScoreCard key={m.cohort} metrics={m} />
        ))}
      </div>

      {chart && <CumulativeChart dates={chart.dates} series={chart.series} />}

      <SimulatedNote />
    </div>
  );
}
