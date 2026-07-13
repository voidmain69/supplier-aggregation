import { useQuery } from '@tanstack/react-query';

import { getSyncAccounts } from '@/shared/api/endpoints';
import { queryKeys } from '@/shared/api/query-keys';

/** Per-account sync status for the monitoring page and the dashboard health card. */
export function useSyncAccounts() {
  return useQuery({
    queryKey: queryKeys.syncAccounts(),
    queryFn: getSyncAccounts,
    staleTime: 15_000,
  });
}
