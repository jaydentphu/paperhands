import type { DecisionOut, LogOut, MetricsOut, PositionOut, RunOut } from './types';

/**
 * The API container publishes port 8000 to the host in both dev
 * (`npm run dev` on 5173, API run separately) and the built app served by
 * the frontend container (docker-compose maps both to localhost) - so one
 * fixed base URL covers both without a proxy. Override with
 * VITE_API_BASE_URL if that ever stops being true (e.g. a real deploy).
 */
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export class ApiError extends Error {
  readonly status: number;
  readonly path: string;

  constructor(status: number, path: string) {
    super(`API request to ${path} failed with status ${status}`);
    this.status = status;
    this.path = path;
  }
}

async function get<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
  const url = new URL(path, BASE_URL);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) url.searchParams.set(key, value);
    }
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new ApiError(response.status, path);
  }
  return (await response.json()) as T;
}

export function getLatestRun(): Promise<RunOut> {
  return get<RunOut>('/runs/latest');
}

export function getDecisions(date?: string): Promise<DecisionOut[]> {
  return get<DecisionOut[]>('/decisions', { date });
}

export function getPositions(status?: 'open' | 'closed'): Promise<PositionOut[]> {
  return get<PositionOut[]>('/positions', { status });
}

export function getMetrics(params?: {
  cohort?: 'A' | 'B' | 'C';
  start?: string;
  end?: string;
}): Promise<MetricsOut[]> {
  return get<MetricsOut[]>('/metrics', params);
}

export function getLogs(runId?: number): Promise<LogOut[]> {
  return get<LogOut[]>('/logs', { run_id: runId?.toString() });
}
