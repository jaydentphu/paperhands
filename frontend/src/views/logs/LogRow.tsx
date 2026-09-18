import { useState } from 'react';
import type { LogLevel, LogOut } from '../../api/types';

const LEVEL_COLOR: Record<LogLevel, string> = {
  debug: 'var(--sage)',
  info: 'var(--text-dim)',
  warning: 'var(--warn)',
  error: 'var(--loss)',
};

function time(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-US', { hour12: false });
}

/** One log row, expandable to a generic pretty-printed JSON payload - real
 * RunLog.payload shapes vary too much per component for a fixed
 * prompt/response layout (see NOTES.md), so this is one panel, not two. */
export function LogRow({ log }: { log: LogOut }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="log-row">
      <button type="button" className="log-row__summary" onClick={() => setOpen(!open)}>
        <span className="log-row__time">{time(log.created_at)}</span>
        <span
          className="log-row__level"
          style={{ color: LEVEL_COLOR[log.level], borderColor: LEVEL_COLOR[log.level] }}
        >
          {log.level.toUpperCase()}
        </span>
        <span className="log-row__comp">{log.component}</span>
        <span className="log-row__msg">{log.message}</span>
        <span className={open ? 'log-row__chevron log-row__chevron--open' : 'log-row__chevron'}>
          ▾
        </span>
      </button>
      {open && (
        <div className="log-row__payload">
          {log.payload === null ? (
            <span className="t-label log-row__no-payload">No payload.</span>
          ) : (
            <pre>{JSON.stringify(log.payload, null, 2)}</pre>
          )}
        </div>
      )}
    </div>
  );
}
