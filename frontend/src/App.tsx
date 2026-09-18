import { NavTabs } from './components/NavTabs';
import { TopBar } from './components/TopBar';
import { RouterProvider, useRouter } from './router';
import { LogsView } from './views/LogsView';
import { PositionsView } from './views/positions/PositionsView';
import { ScoreboardView } from './views/scoreboard/ScoreboardView';
import { TodayView } from './views/today/TodayView';

function CurrentView() {
  const { route } = useRouter();
  switch (route) {
    case '/':
      return <TodayView />;
    case '/positions':
      return <PositionsView />;
    case '/scoreboard':
      return <ScoreboardView />;
    case '/logs':
      return <LogsView />;
  }
}

function Shell() {
  return (
    <div className="app-shell">
      <div className="app-shell__glow app-shell__glow--teal" aria-hidden="true" />
      <div className="app-shell__glow app-shell__glow--violet" aria-hidden="true" />
      <div className="app-shell__content">
        <TopBar />
        <NavTabs />
        <main>
          <CurrentView />
        </main>
      </div>
    </div>
  );
}

export function App() {
  return (
    <RouterProvider>
      <Shell />
    </RouterProvider>
  );
}
