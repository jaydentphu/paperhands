/**
 * Wordmark, search field (visual only - no search feature is in scope),
 * and status pills. Layout/spec: docs/design/STYLE_GUIDE.md "Layout"
 * section - 72px tall, wordmark+search left, pills right, flexible
 * spacer between.
 */
export function TopBar() {
  return (
    <div className="top-bar">
      <div className="top-bar__brand">
        <div className="top-bar__mark" aria-hidden="true">
          <div className="top-bar__mark-cut" />
        </div>
        <div className="top-bar__title">Paper Hands</div>
      </div>

      <div className="top-bar__search" aria-hidden="true">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <circle cx="6" cy="6" r="4.4" stroke="#7d8798" strokeWidth="1.4" />
          <line x1="9.4" y1="9.4" x2="12.6" y2="12.6" stroke="#7d8798" strokeWidth="1.4" />
        </svg>
        <span className="top-bar__search-text">Search tickers, runs, decisions</span>
      </div>

      <div className="top-bar__spacer" />

      <div className="pill pill--accent">
        <span className="pill__dot" />
        Run complete
      </div>
      <div className="pill">Next run 10:30 ET</div>
      <div className="pill">Read-only · No live trading</div>
    </div>
  );
}
