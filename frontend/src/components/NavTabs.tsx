import type { Route } from '../router';
import { useRouter } from '../router';

const TABS: readonly { route: Route; label: string }[] = [
  { route: '/', label: 'Today' },
  { route: '/positions', label: 'Positions' },
  { route: '/scoreboard', label: 'Scoreboard' },
  { route: '/logs', label: 'Logs' },
];

/** The design canvas's fifth tab, "Style guide," is a design-tool
 * artifact for exporting tokens - not one of PRD section 4's four
 * required views - so it has no tab here. */
export function NavTabs() {
  const { route, navigate } = useRouter();

  return (
    <div className="nav-tabs">
      {TABS.map((tab) => (
        <button
          key={tab.route}
          type="button"
          className={`nav-tabs__tab ${route === tab.route ? 'nav-tabs__tab--active' : ''}`}
          onClick={() => navigate(tab.route)}
        >
          {tab.label}
        </button>
      ))}
      <div className="nav-tabs__spacer" />
    </div>
  );
}
