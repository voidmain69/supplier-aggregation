import { useQueue } from '@/entities/curation/use-queue';
import type { CurationItem } from '@/shared/api/types';

export interface QueueNeighbours {
  current: CurationItem | undefined;
  next: CurationItem | undefined;
  prev: CurationItem | undefined;
}

/**
 * Locate the current item in the cached queue and its neighbours, so a decision can jump
 * straight to the next pending item (keyboard-first flow, curation-ui-plan §3.3). Reads the
 * already-loaded queue cache — no extra request.
 */
export function useQueueNav(supplierProductId: string): QueueNeighbours {
  const { items } = useQueue();
  const index = items.findIndex((item) => item.supplier_product_id === supplierProductId);
  if (index === -1) return { current: undefined, next: undefined, prev: undefined };
  return {
    current: items[index],
    next: items[index + 1],
    prev: index > 0 ? items[index - 1] : undefined,
  };
}
