/**
 * Standard cursor-pagination hook over the `Page[T]` envelope (curation-ui-plan §4.3): the
 * cursor is an opaque black box, passed back verbatim; `next_cursor === null` ends the list.
 */

import { useInfiniteQuery, type QueryKey } from '@tanstack/react-query';

import type { Page } from './types';

export function useCursorQuery<T>(
  key: QueryKey,
  fetchPage: (cursor: string | null) => Promise<Page<T>>,
  options: { staleTime?: number; enabled?: boolean } = {},
) {
  const query = useInfiniteQuery({
    queryKey: key,
    queryFn: ({ pageParam }) => fetchPage(pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_cursor,
    staleTime: options.staleTime,
    enabled: options.enabled,
  });

  const items = query.data?.pages.flatMap((page) => page.items) ?? [];
  const totalEstimate = query.data?.pages[0]?.total_estimate ?? null;

  return { ...query, items, totalEstimate };
}
