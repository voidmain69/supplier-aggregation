import type { UseQueryResult } from '@tanstack/react-query';
import type { ReactNode } from 'react';

import { ProblemAlert } from './problem-alert';

/**
 * One standard loading→error→data wrapper so every screen gets the same three states without
 * re-inventing them (curation-ui-plan §5). Pass a skeleton for `loading`.
 */
export function QueryBoundary<T>({
  query,
  loading,
  children,
}: {
  query: UseQueryResult<T>;
  loading: ReactNode;
  children: (data: T) => ReactNode;
}) {
  if (query.isPending) return <>{loading}</>;
  if (query.isError) {
    return <ProblemAlert error={query.error} onRetry={() => void query.refetch()} />;
  }
  return <>{children(query.data)}</>;
}
