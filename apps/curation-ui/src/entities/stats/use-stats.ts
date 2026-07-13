import { useQuery } from '@tanstack/react-query';

import { getCurationStats } from '@/shared/api/endpoints';
import { queryKeys } from '@/shared/api/query-keys';

/** Dashboard aggregate counts (queue depth, canonical total, decisions by action). */
export function useStats() {
  return useQuery({
    queryKey: queryKeys.curationStats(),
    queryFn: getCurationStats,
    staleTime: 30_000,
  });
}
