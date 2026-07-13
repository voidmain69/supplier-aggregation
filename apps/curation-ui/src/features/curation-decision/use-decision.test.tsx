import { QueryClient, QueryClientProvider, type InfiniteData } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import { http as mswHttp, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import type { ReactNode } from 'react';
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest';

import { queryKeys } from '@/shared/api/query-keys';
import type { CurationItem, Page } from '@/shared/api/types';

import { useCreateNew, useDecide } from './use-decision';

const BASE = 'http://localhost:8080';

function item(id: string): CurationItem {
  return {
    supplier_product_id: id,
    canonical_product_id: `canon-${id}`,
    method: 'rag_suggested',
    confidence: 0.7,
    status: 'pending_review',
  };
}

const server = setupServer();

beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' });
});
afterEach(() => {
  server.resetHandlers();
});
afterAll(() => {
  server.close();
});

function seededClient(ids: string[]): QueryClient {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const data: InfiniteData<Page<CurationItem>> = {
    pages: [{ items: ids.map(item), next_cursor: null, total_estimate: null }],
    pageParams: [null],
  };
  client.setQueryData(queryKeys.curationQueue(), data);
  return client;
}

function wrapper(client: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

function queueIds(client: QueryClient): string[] {
  const data = client.getQueryData<InfiniteData<Page<CurationItem>>>(queryKeys.curationQueue());
  return (data?.pages ?? []).flatMap((p) => p.items.map((i) => i.supplier_product_id));
}

describe('useDecide', () => {
  it('confirms a link and removes it from the queue cache', async () => {
    server.use(
      mswHttp.post(`${BASE}/v1/curation/links/:id/confirm`, ({ params }) =>
        HttpResponse.json({
          supplier_product_id: params.id,
          canonical_product_id: `canon-${String(params.id)}`,
          status: 'confirmed',
        }),
      ),
    );
    const client = seededClient(['a', 'b', 'c']);
    const { result } = renderHook(() => useDecide(), { wrapper: wrapper(client) });

    await result.current('b', 'confirm');

    await waitFor(() => {
      expect(queueIds(client)).toEqual(['a', 'c']);
    });
  });

  it('rolls back the optimistic removal when the write fails with a server error', async () => {
    server.use(
      mswHttp.post(`${BASE}/v1/curation/links/:id/reject`, () =>
        HttpResponse.json(
          { type: 't', title: 'x', status: 500, detail: 'boom' },
          { status: 500, headers: { 'content-type': 'application/problem+json' } },
        ),
      ),
    );
    const client = seededClient(['a', 'b']);
    const { result } = renderHook(() => useDecide(), { wrapper: wrapper(client) });

    await result.current('a', 'reject');

    // Optimistically removed, then restored on failure.
    await waitFor(() => {
      expect(queueIds(client)).toEqual(['a', 'b']);
    });
  });

  it('create-new drops the item on success and rolls back on failure', async () => {
    // First call succeeds, second returns a GTIN conflict.
    server.use(
      mswHttp.post(`${BASE}/v1/curation/links/a/create-new`, () =>
        HttpResponse.json({
          supplier_product_id: 'a',
          canonical_product_id: 'new-1',
          status: 'confirmed',
        }),
      ),
      mswHttp.post(`${BASE}/v1/curation/links/b/create-new`, () =>
        HttpResponse.json(
          { type: 't', title: 'x', status: 409, detail: 'gtin exists' },
          { status: 409, headers: { 'content-type': 'application/problem+json' } },
        ),
      ),
    );
    const client = seededClient(['a', 'b']);
    const { result } = renderHook(() => useCreateNew(), { wrapper: wrapper(client) });

    await result.current('a', { title: 'New Product', brand: null, gtin: null });
    await waitFor(() => {
      expect(queueIds(client)).toEqual(['b']);
    });

    // A failure re-throws and restores the optimistic removal.
    await expect(
      result.current('b', { title: 'Dup', brand: null, gtin: '04006381333931' }),
    ).rejects.toBeTruthy();
    await waitFor(() => {
      expect(queueIds(client)).toEqual(['b']);
    });
  });

  it('keeps a 409-conflicted item removed (already decided elsewhere)', async () => {
    server.use(
      mswHttp.post(`${BASE}/v1/curation/links/:id/confirm`, () =>
        HttpResponse.json(
          { type: 't', title: 'x', status: 409, detail: 'already decided' },
          { status: 409, headers: { 'content-type': 'application/problem+json' } },
        ),
      ),
    );
    const client = seededClient(['a', 'b']);
    const { result } = renderHook(() => useDecide(), { wrapper: wrapper(client) });

    await result.current('a', 'confirm');

    await waitFor(() => {
      expect(queueIds(client)).toEqual(['b']);
    });
  });
});
