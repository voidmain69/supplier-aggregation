import { getCurationQueue } from '@/shared/api/endpoints';
import { queryKeys } from '@/shared/api/query-keys';
import { useCursorQuery } from '@/shared/api/use-cursor-query';
import type { CurationItem } from '@/shared/api/types';

const PAGE = 50;

/** The curation queue as an infinite, cursor-paginated list. */
export function useQueue() {
  return useCursorQuery<CurationItem>(
    queryKeys.curationQueue(),
    (cursor) => getCurationQueue({ cursor, limit: PAGE }),
    { staleTime: 30_000 }, // 30s: the queue changes slowly; avoid churn between decisions.
  );
}
