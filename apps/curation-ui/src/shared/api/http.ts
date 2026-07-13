/**
 * The single HTTP entry point (curation-ui-plan §4.3). Every network call goes through here;
 * raw `fetch` elsewhere is blocked by ESLint. Responsibilities, all centralized:
 *   - attach the bearer token and a W3C `traceparent` so a failure links to backend traces;
 *   - stamp an `Idempotency-Key` on mutations so a retried POST is safe;
 *   - parse RFC 9457 problem+json into a typed {@link ApiError} (carrying `trace_id`);
 *   - honour a `429 Retry-After` with one automatic retry;
 *   - surface `401` distinctly so the app can drop the session.
 */

import { config } from '@/shared/config/env';
import { ulid } from '@/shared/lib/ulid';

import { tokenStore } from './token';
import type { ApiProblem } from './types';

/** A typed problem+json failure. `problem` is null for transport/opaque errors. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly problem: ApiProblem | null,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }

  get traceId(): string | null {
    return this.problem?.trace_id ?? null;
  }

  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  /** Confirm/reject race: the item was already decided by someone else (or an earlier click). */
  get isConflict(): boolean {
    return this.status === 409;
  }
}

export type QueryValue = string | number | boolean | null | undefined;

export interface RequestOptions {
  params?: Record<string, QueryValue>;
  /** True for confirm/reject; adds an Idempotency-Key so the write is safely retryable. */
  idempotent?: boolean;
  signal?: AbortSignal;
}

function randomHex(bytes: number): string {
  const buf = new Uint8Array(bytes);
  crypto.getRandomValues(buf);
  return Array.from(buf, (b) => b.toString(16).padStart(2, '0')).join('');
}

/** Generate a W3C traceparent so the gateway/services can correlate this call in Tempo. */
function traceparent(): string {
  return `00-${randomHex(16)}-${randomHex(8)}-01`;
}

function buildUrl(path: string, params?: Record<string, QueryValue>): string {
  const url = new URL(config.apiBaseUrl + path);
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== null && value !== undefined) url.searchParams.set(key, String(value));
  }
  return url.toString();
}

async function toApiError(res: Response): Promise<ApiError> {
  let problem: ApiProblem | null = null;
  try {
    const body: unknown = await res.json();
    if (body && typeof body === 'object' && 'status' in body) problem = body as ApiProblem;
  } catch {
    // Non-JSON error body (e.g. a proxy 502 HTML page) — keep problem null.
  }
  return new ApiError(res.status, problem, problem?.detail ?? `HTTP ${String(res.status)}`);
}

async function once(method: string, url: string, opts: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = { traceparent: traceparent() };
  const token = tokenStore.get();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (opts.idempotent) headers['Idempotency-Key'] = ulid();
  return fetch(url, { method, headers, signal: opts.signal });
}

async function request<T>(method: string, path: string, opts: RequestOptions = {}): Promise<T> {
  const url = buildUrl(path, opts.params);
  let res = await once(method, url, opts);

  // One polite retry on rate-limit, respecting Retry-After (curation-ui-plan §4.3, §8).
  if (res.status === 429) {
    const retryAfter = Number(res.headers.get('Retry-After') ?? '1');
    await new Promise((r) => setTimeout(r, Math.min(retryAfter, 5) * 1000));
    res = await once(method, url, opts);
  }

  if (res.status === 401) tokenStore.clear();
  if (!res.ok) throw await toApiError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const http = {
  get: <T>(path: string, opts?: RequestOptions): Promise<T> => request<T>('GET', path, opts),
  post: <T>(path: string, opts?: RequestOptions): Promise<T> =>
    request<T>('POST', path, { ...opts, idempotent: true }),
};
