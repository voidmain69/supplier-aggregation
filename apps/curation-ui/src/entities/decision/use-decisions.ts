import { getDecisions } from '@/shared/api/endpoints';
import { queryKeys } from '@/shared/api/query-keys';
import type { Decision } from '@/shared/api/types';
import { useCursorQuery } from '@/shared/api/use-cursor-query';

const PAGE = 50;

/** The curation decision journal as an infinite, cursor-paginated list (newest first). */
export function useDecisions() {
  return useCursorQuery<Decision>(
    queryKeys.decisions(),
    (cursor) => getDecisions({ cursor, limit: PAGE }),
    { staleTime: 15_000 },
  );
}
