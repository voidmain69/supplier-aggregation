import { useMutation, useQueryClient } from '@tanstack/react-query';

import { triggerSync } from '@/shared/api/endpoints';
import { ApiError } from '@/shared/api/http';
import { queryKeys } from '@/shared/api/query-keys';
import type { TriggerResult } from '@/shared/api/types';
import { t } from '@/shared/config/i18n';
import { toast } from '@/shared/ui/toast';

/** Manually request a sync for an account; refetch the account list on success. */
export function useTriggerSync() {
  const qc = useQueryClient();

  return useMutation<TriggerResult, unknown, string>({
    mutationFn: (accountId) => triggerSync(accountId),
    onSuccess: () => {
      toast.success(t.sync.triggered);
      void qc.invalidateQueries({ queryKey: queryKeys.syncAccounts() });
    },
    onError: (error) => {
      const message =
        error instanceof ApiError ? (error.problem?.detail ?? error.message) : t.common.errorTitle;
      toast.error(message);
    },
  });
}
