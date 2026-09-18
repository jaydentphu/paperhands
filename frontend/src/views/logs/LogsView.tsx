import { useMemo, useState } from 'react';
import { getLatestRun, getLogs } from '../../api/client';
import { useFetch } from '../../api/useFetch';
import { LogRow } from './LogRow';
import './logs.css';

const ALL = 'All';

export function LogsView() {
  const runState = useFetch(() => getLatestRun(), []);
  const logsState = useFetch(() => getLogs(), []);
  const [component, setComponent] = useState(ALL);

  const components = useMemo(() => {
    if (logsState.status !== 'ready') return [];
    return [...new Set(logsState.data.map((l) => l.component))].sort();
  }, [logsState]);

  const rows = useMemo(() => {
    if (logsState.status !== 'ready') return [];
    return component === ALL
      ? logsState.data
      : logsState.data.filter((l) => l.component === component);
  }, [logsState, component]);

  if (logsState.status === 'loading') {
    return (
      <div className="view-placeholder">
        <p className="t-body view-placeholder__note">Loading logs…</p>
      </div>
    );
  }

  if (logsState.status === 'error') {
    return (
      <div className="view-placeholder">
        <h1 className="t-h1">Logs</h1>
        <p className="t-body view-placeholder__note">Could not reach the API: {logsState.error}</p>
      </div>
    );
  }

  return (
    <div className="logs-view">
      <div className="logs-view__header">
        <div className="t-h1">Logs</div>
        <div className="t-label logs-view__count">{rows.length} entries</div>
        <div className="logs-view__spacer" />
        {runState.status === 'ready' && (
          <div className="t-label">Run {runState.data.run_date}</div>
        )}
      </div>

      {components.length > 1 && (
        <div className="logs-view__filters">
          <span className="t-micro">Component</span>
          {[ALL, ...components].map((c) => (
            <button
              key={c}
              type="button"
              className={c === component ? 'log-filter log-filter--active' : 'log-filter'}
              onClick={() => setComponent(c)}
            >
              {c}
            </button>
          ))}
        </div>
      )}

      <div className="logs-table">
        {rows.length === 0 ? (
          <div className="t-label logs-table__empty">No log entries.</div>
        ) : (
          rows.map((log) => <LogRow key={log.id} log={log} />)
        )}
      </div>
    </div>
  );
}
