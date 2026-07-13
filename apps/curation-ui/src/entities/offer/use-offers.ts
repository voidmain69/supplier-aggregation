import { useQuery } from '@tanstack/react-query';

import { listProductOffers } from '@/shared/api/endpoints';
import { queryKeys } from '@/shared/api/query-keys';

/** Offers (price + availability) for one supplier product, across all accounts. */
export function useProductOffers(supplierProductId: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.productOffers(supplierProductId),
    queryFn: () => listProductOffers(supplierProductId, { limit: 50 }),
    enabled: enabled && supplierProductId !== '',
    staleTime: 60_000,
  });
}
