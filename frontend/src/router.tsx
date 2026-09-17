import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';

/**
 * Deliberately hand-rolled, not react-router: CLAUDE.md's stack list says
 * "no other frameworks" for the frontend, and four fixed routes with no
 * nesting or params don't need one.
 */
export type Route = '/' | '/positions' | '/scoreboard' | '/logs';

const ROUTES: readonly Route[] = ['/', '/positions', '/scoreboard', '/logs'];

function normalize(path: string): Route {
  return (ROUTES as readonly string[]).includes(path) ? (path as Route) : '/';
}

interface RouterContextValue {
  route: Route;
  navigate: (route: Route) => void;
}

const RouterContext = createContext<RouterContextValue | null>(null);

export function RouterProvider({ children }: { children: ReactNode }) {
  const [route, setRoute] = useState<Route>(() => normalize(window.location.pathname));

  useEffect(() => {
    const onPopState = () => setRoute(normalize(window.location.pathname));
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  const navigate = (next: Route): void => {
    if (next !== route) {
      window.history.pushState(null, '', next);
    }
    setRoute(next);
  };

  return <RouterContext.Provider value={{ route, navigate }}>{children}</RouterContext.Provider>;
}

export function useRouter(): RouterContextValue {
  const ctx = useContext(RouterContext);
  if (ctx === null) {
    throw new Error('useRouter must be used within a RouterProvider');
  }
  return ctx;
}
