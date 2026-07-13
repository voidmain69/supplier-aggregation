import { useNavigate, useParams } from '@tanstack/react-router';
import { useState } from 'react';

import { CanonicalProductCard } from '@/entities/canonical-product/canonical-product-card';
import { useCanonicalProduct } from '@/entities/canonical-product/use-canonical-product';
import { useSupplierProductsByCanonical } from '@/entities/supplier-product/use-supplier-product';
import { MergeDialog } from '@/features/canonical-merge/merge-dialog';
import { OffersPanel } from '@/features/commercial-context/offers-panel';
import { t } from '@/shared/config/i18n';
import { Button } from '@/shared/ui/button';
import { Card, CardBody, CardHeader } from '@/shared/ui/card';
import { Mono } from '@/shared/ui/mono';
import { ProblemAlert } from '@/shared/ui/problem-alert';
import { Skeleton } from '@/shared/ui/skeleton';

const ROUTE = '/canonical/$canonicalId' as const;

export function CanonicalDetailPage() {
  const { canonicalId } = useParams({ from: ROUTE });
  const navigate = useNavigate();
  const canonical = useCanonicalProduct(canonicalId);
  const linked = useSupplierProductsByCanonical(canonicalId);
  const [mergeOpen, setMergeOpen] = useState(false);

  return (
    <div className="mx-auto max-w-4xl p-4">
      <div className="mb-4 flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={() => void navigate({ to: '/canonical' })}>
          ← {t.canonical.title}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setMergeOpen(true);
          }}
        >
          {t.canonical.merge}
        </Button>
      </div>

      <MergeDialog
        open={mergeOpen}
        targetCanonicalId={canonicalId}
        onClose={() => {
          setMergeOpen(false);
        }}
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>{t.review.candidateSide}</CardHeader>
          <CardBody>
            {canonical.isPending ? (
              <Skeleton className="h-32 w-full" />
            ) : canonical.isError ? (
              <ProblemAlert error={canonical.error} onRetry={() => void canonical.refetch()} />
            ) : (
              <CanonicalProductCard product={canonical.data} />
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader>{t.review.linkedProducts}</CardHeader>
          <CardBody>
            {linked.isPending ? (
              <Skeleton className="h-32 w-full" />
            ) : linked.isError ? (
              <ProblemAlert error={linked.error} onRetry={() => void linked.refetch()} />
            ) : linked.data.items.length === 0 ? (
              <p className="text-sm text-muted">{t.common.none}</p>
            ) : (
              <ul className="flex flex-col gap-2">
                {linked.data.items.map((sp) => (
                  <li
                    key={sp.supplier_product_id}
                    className="border-b border-border pb-2 last:border-0"
                  >
                    <div className="text-sm font-medium text-text">{sp.name}</div>
                    <div className="text-xs text-muted">
                      {sp.supplier_code} · <Mono value={sp.gtin} />
                    </div>
                    <div className="mt-1">
                      <OffersPanel supplierProductId={sp.supplier_product_id} />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
