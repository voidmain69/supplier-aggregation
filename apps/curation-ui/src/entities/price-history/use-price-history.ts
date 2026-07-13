import { useQuery } from '@tanstack/react-query';

import { getOfferPriceHistory } from '@/shared/api/endpoints';
import { queryKeys } from '@/shared/api/query-keys';

/** Price points for one offer (used to draw a sparkline in the review commercial context). */
export function usePriceHistory(offerId: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.priceHistory(offerId),
    queryFn: () => getOfferPriceHistory(offerId, { limit: 100 }),
    enabled: enabled && offerId !== '',
    staleTime: 5 * 60_000,
  });
}
