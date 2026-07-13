import { useNavigate } from '@tanstack/react-router';
import { useQueryClient } from '@tanstack/react-query';

import { ConfidenceBadge } from '@/entities/curation/confidence-badge';
import { MethodBadge } from '@/entities/curation/method-badge';
import { useCanonicalProduct } from '@/entities/canonical-product/use-canonical-product';
import { useSupplierProduct } from '@/entities/supplier-product/use-supplier-product';
import { getCanonicalProduct, getSupplierProduct } from '@/shared/api/endpoints';
import { queryKeys } from '@/shared/api/query-keys';
import type { CurationItem } from '@/shared/api/types';
import { cn } from '@/shared/ui/cn';
import { Mono } from '@/shared/ui/mono';
import { Skeleton } from '@/shared/ui/skeleton';

/**
 * One queue row. The queue payload has no product titles, so each row fetches the supplier
 * product and candidate canonical it references (the documented N+1; removed once the queue
 * embeds snapshots — curation-ui-plan §2.4). Hovering/focusing prefetches the review data so
 * opening it is instant (§8).
 */
export function QueueRow({ item, selected }: { item: CurationItem; selected: boolean }) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const product = useSupplierProduct(item.supplier_product_id);
  const canonical = useCanonicalProduct(item.canonical_product_id);

  function open() {
    void navigate({
      to: '/queue/$supplierProductId',
      params: { supplierProductId: item.supplier_product_id },
    });
  }

  function prefetch() {
    void qc.prefetchQuery({
      queryKey: queryKeys.supplierProduct(item.supplier_product_id),
      queryFn: () => getSupplierProduct(item.supplier_product_id),
    });
    void qc.prefetchQuery({
      queryKey: queryKeys.canonicalProduct(item.canonical_product_id),
      queryFn: () => getCanonicalProduct(item.canonical_product_id),
    });
  }

  return (
    <tr
      onClick={open}
      onMouseEnter={prefetch}
      onFocus={prefetch}
      className={cn(
        'cursor-pointer border-b border-border transition-colors hover:bg-surface-2',
        selected && 'bg-surface-2',
      )}
    >
      <td className="px-3 py-2">
        {product.isPending ? (
          <Skeleton className="h-4 w-48" />
        ) : product.isError ? (
          <Mono value={item.supplier_product_id} />
        ) : (
          <div>
            <div className="text-sm font-medium text-text">{product.data.name}</div>
            <div className="text-xs text-muted">{product.data.brand ?? ''}</div>
          </div>
        )}
      </td>
      <td className="px-3 py-2">
        {canonical.isPending ? (
          <Skeleton className="h-4 w-40" />
        ) : canonical.isError ? (
          <Mono value={item.canonical_product_id} />
        ) : (
          <span className="text-sm text-text">{canonical.data.title}</span>
        )}
      </td>
      <td className="px-3 py-2">
        <MethodBadge method={item.method} />
      </td>
      <td className="px-3 py-2">
        <ConfidenceBadge confidence={item.confidence} />
      </td>
    </tr>
  );
}
