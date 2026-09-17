import { useEffect, useState } from 'react';

export type FetchState<T> =
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'ready'; data: T };

/**
 * Re-runs `fetcher` whenever `deps` changes, tracking loading/error/ready.
 * Ignores results from a stale call that resolves after a newer one started.
 */
export function useFetch<T>(fetcher: () => Promise<T>, deps: readonly unknown[]): FetchState<T> {
  const [state, setState] = useState<FetchState<T>>({ status: 'loading' });

  useEffect(() => {
    let cancelled = false;
    setState({ status: 'loading' });
    fetcher()
      .then((data) => {
        if (!cancelled) setState({ status: 'ready', data });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : 'request failed';
          setState({ status: 'error', error: message });
        }
      });
    return () => {
      cancelled = true;
    };
  }, deps);

  return state;
}
