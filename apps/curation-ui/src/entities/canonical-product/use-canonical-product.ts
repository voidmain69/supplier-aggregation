import { useQuery } from '@tanstack/react-query';

import { getCanonicalProduct, listCanonicalProducts } from '@/shared/api/endpoints';
import { queryKeys } from '@/shared/api/query-keys';
import { useCursorQuery } from '@/shared/api/use-cursor-query';
import type { CanonicalProduct } from '@/shared/api/types';

export function useCanonicalProduct(id: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.canonicalProduct(id),
    queryFn: () => getCanonicalProduct(id),
    enabled: enabled && id !== '',
    staleTime: 5 * 60_000,
  });
}

/** Canonical catalog list, optionally filtered by GTIN-14. */
export function useCanonicalList(gtin: string) {
  return useCursorQuery<CanonicalProduct>(
    queryKeys.canonicalList(gtin),
    (cursor) => listCanonicalProducts({ gtin: gtin || undefined, cursor, limit: 50 }),
    { staleTime: 60_000 },
  );
}
