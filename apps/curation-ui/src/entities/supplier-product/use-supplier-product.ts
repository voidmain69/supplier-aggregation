import { useQuery } from '@tanstack/react-query';

import { getSupplierProduct, listSupplierProducts } from '@/shared/api/endpoints';
import { queryKeys } from '@/shared/api/query-keys';

const CARD_STALE = 5 * 60_000; // 5 min: product cards are cheap to keep warm.

export function useSupplierProduct(id: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.supplierProduct(id),
    queryFn: () => getSupplierProduct(id),
    enabled: enabled && id !== '',
    staleTime: CARD_STALE,
  });
}

/** All supplier products mapped to one canonical product (the "linked products" panel). */
export function useSupplierProductsByCanonical(canonicalId: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.supplierProductsByCanonical(canonicalId),
    queryFn: () => listSupplierProducts({ canonicalProductId: canonicalId, limit: 50 }),
    enabled: enabled && canonicalId !== '',
    staleTime: CARD_STALE,
  });
}
