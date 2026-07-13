/**
 * Confirm/reject a curation link with an optimistic queue update (curation-ui-plan §3.3, §8):
 * the item leaves the queue immediately so the operator can move to the next one, and the write
 * settles in the background.
 *
 * The settle logic is a plain promise driven off the query client — NOT useMutation's observer
 * callbacks — precisely because we navigate away (unmounting) the instant we optimistically
 * remove the item. An observer's callbacks can be dropped on unmount; this always runs to
 * completion, so rollback and toasts are guaranteed. A 409/404 (already decided elsewhere) is
 * not a rollback: the item is genuinely gone, so we keep it removed and inform quietly.
 */

import { useQueryClient, type InfiniteData } from '@tanstack/react-query';
import { useCallback } from 'react';

import { confirmLink, createNewCanonical, rejectLink } from '@/shared/api/endpoints';
import { ApiError } from '@/shared/api/http';
import { queryKeys } from '@/shared/api/query-keys';
import type { CreateCanonicalInput, CurationItem, Page } from '@/shared/api/types';
import { t } from '@/shared/config/i18n';
import { toast } from '@/shared/ui/toast';

export type Decision = 'confirm' | 'reject';

type QueueData = InfiniteData<Page<CurationItem>>;

function dropItem(data: QueueData | undefined, id: string): QueueData | undefined {
  if (!data) return data;
  return {
    ...data,
    pages: data.pages.map((page) => ({
      ...page,
      items: page.items.filter((item) => item.supplier_product_id !== id),
    })),
  };
}

export function useDecide() {
  const qc = useQueryClient();

  return useCallback(
    async (id: string, decision: Decision): Promise<void> => {
      const key = queryKeys.curationQueue();
      await qc.cancelQueries({ queryKey: key });
      const prev = qc.getQueryData<QueueData>(key);
      qc.setQueryData<QueueData>(key, (data) => dropItem(data, id));

      try {
        const result = await (decision === 'confirm' ? confirmLink(id) : rejectLink(id));
        toast.success(decision === 'confirm' ? t.review.confirmed : t.review.rejected);
        void qc.invalidateQueries({
          queryKey: queryKeys.canonicalProduct(result.canonical_product_id),
        });
      } catch (error) {
        if (error instanceof ApiError && (error.isConflict || error.status === 404)) {
          toast.info(error.problem?.detail ?? t.review.alreadyDecided('?'));
          return;
        }
        qc.setQueryData<QueueData>(key, prev); // real failure — undo the optimistic removal
        const message =
          error instanceof ApiError
            ? (error.problem?.detail ?? error.message)
            : t.common.errorTitle;
        toast.error(message);
      }
    },
    [qc],
  );
}

/**
 * Create a new canonical from a curation item. Like a decision, it resolves the queue entry, so
 * it optimistically drops the item and settles in the background. Throws on failure so the caller
 * (a form dialog) can stay open and surface the problem detail.
 */
export function useCreateNew() {
  const qc = useQueryClient();

  return useCallback(
    async (id: string, body: CreateCanonicalInput): Promise<void> => {
      const key = queryKeys.curationQueue();
      await qc.cancelQueries({ queryKey: key });
      const prev = qc.getQueryData<QueueData>(key);
      qc.setQueryData<QueueData>(key, (data) => dropItem(data, id));
      try {
        await createNewCanonical(id, body);
        toast.success(t.review.created);
      } catch (error) {
        qc.setQueryData<QueueData>(key, prev); // undo optimistic removal; the dialog stays open
        throw error;
      }
    },
    [qc],
  );
}
