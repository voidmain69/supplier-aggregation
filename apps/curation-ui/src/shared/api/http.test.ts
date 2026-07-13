import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError, http } from './http';
import { tokenStore } from './token';

interface FetchCall {
  url: string;
  init: RequestInit;
}

function mockFetchOnce(...responses: Response[]): FetchCall[] {
  const calls: FetchCall[] = [];
  let i = 0;
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init: RequestInit) => {
      calls.push({ url, init });
      const res = responses[Math.min(i, responses.length - 1)];
      i += 1;
      return Promise.resolve(res);
    }),
  );
  return calls;
}

function problem(status: number, detail: string, traceId?: string): Response {
  return new Response(
    JSON.stringify({ type: 't', title: 'x', status, detail, trace_id: traceId ?? null }),
    { status, headers: { 'content-type': 'application/problem+json' } },
  );
}

beforeEach(() => {
  tokenStore.clear();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('http', () => {
  it('attaches the bearer token and a traceparent, and returns parsed JSON', async () => {
    tokenStore.set('secret-token');
    const calls = mockFetchOnce(new Response(JSON.stringify({ ok: true }), { status: 200 }));

    const body = await http.get<{ ok: boolean }>('/v1/curation/queue');

    expect(body.ok).toBe(true);
    const headers = calls[0]?.init.headers as Record<string, string>;
    expect(headers.Authorization).toBe('Bearer secret-token');
    expect(headers.traceparent).toMatch(/^00-[0-9a-f]{32}-[0-9a-f]{16}-01$/);
  });

  it('parses problem+json into an ApiError carrying detail and trace id', async () => {
    mockFetchOnce(problem(404, 'No such item.', 'abc123'));

    await expect(http.get('/v1/curation/queue')).rejects.toMatchObject({
      status: 404,
      traceId: 'abc123',
    });
    await expect(http.get('/v1/curation/queue')).rejects.toBeInstanceOf(ApiError);
  });

  it('clears the session on 401', async () => {
    tokenStore.set('stale');
    mockFetchOnce(problem(401, 'Token revoked.'));

    await expect(http.get('/v1/curation/queue')).rejects.toBeInstanceOf(ApiError);
    expect(tokenStore.get()).toBeNull();
  });

  it('retries once on 429 respecting Retry-After, then succeeds', async () => {
    const rateLimited = new Response('{}', {
      status: 429,
      headers: { 'content-type': 'application/problem+json', 'Retry-After': '0' },
    });
    const ok = new Response(JSON.stringify({ ok: true }), { status: 200 });
    const calls = mockFetchOnce(rateLimited, ok);

    const body = await http.get<{ ok: boolean }>('/v1/curation/queue');

    expect(body.ok).toBe(true);
    expect(calls).toHaveLength(2);
  });

  it('stamps an Idempotency-Key on POST', async () => {
    const calls = mockFetchOnce(
      new Response(
        JSON.stringify({
          supplier_product_id: '1',
          canonical_product_id: '2',
          status: 'confirmed',
        }),
        {
          status: 200,
        },
      ),
    );

    await http.post('/v1/curation/links/1/confirm');

    const headers = calls[0]?.init.headers as Record<string, string>;
    expect(headers['Idempotency-Key']).toBeTruthy();
  });
});
