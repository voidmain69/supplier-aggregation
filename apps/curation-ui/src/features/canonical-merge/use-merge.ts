import { useMutation, useQueryClient } from '@tanstack/react-query';

import { mergeCanonical } from '@/shared/api/endpoints';
import { ApiError } from '@/shared/api/http';
import { queryKeys } from '@/shared/api/query-keys';
import type { MergeResult } from '@/shared/api/types';
import { t } from '@/shared/config/i18n';
import { toast } from '@/shared/ui/toast';

/**
 * Merge a source canonical into a target. On success, invalidate both canonical entries and any
 * canonical list so the removed source and the target's new links refetch.
 */
export function useMerge(targetCanonicalId: string) {
  const qc = useQueryClient();

  return useMutation<MergeResult, unknown, string>({
    mutationFn: (sourceCanonicalId) => mergeCanonical(targetCanonicalId, sourceCanonicalId),
    onSuccess: (result) => {
      toast.success(t.canonical.merged(result.moved_links));
      void qc.invalidateQueries({ queryKey: queryKeys.canonicalProduct(targetCanonicalId) });
      void qc.invalidateQueries({ queryKey: ['canonical-products'] });
    },
    onError: (error) => {
      const message =
        error instanceof ApiError ? (error.problem?.detail ?? error.message) : t.common.errorTitle;
      toast.error(message);
    },
  });
}
