import { useNavigate, useParams, useSearch } from '@tanstack/react-router';
import { useState } from 'react';

import { AttributeDiffTable } from '@/entities/attribute-diff/attribute-diff-table';
import { CanonicalProductCard } from '@/entities/canonical-product/canonical-product-card';
import { useCanonicalProduct } from '@/entities/canonical-product/use-canonical-product';
import { ConfidenceBadge } from '@/entities/curation/confidence-badge';
import { MethodBadge } from '@/entities/curation/method-badge';
import { SupplierProductCard } from '@/entities/supplier-product/supplier-product-card';
import {
  useSupplierProduct,
  useSupplierProductsByCanonical,
} from '@/entities/supplier-product/use-supplier-product';
import { OffersPanel } from '@/features/commercial-context/offers-panel';
import { CreateNewDialog } from '@/features/curation-decision/create-new-dialog';
import { useDecide, type Decision } from '@/features/curation-decision/use-decision';
import type { CurationItem } from '@/shared/api/types';
import { t } from '@/shared/config/i18n';
import { useHotkeys } from '@/shared/lib/use-hotkeys';
import { Button } from '@/shared/ui/button';
import { Card, CardBody, CardHeader } from '@/shared/ui/card';
import { Kbd } from '@/shared/ui/kbd';
import { Mono } from '@/shared/ui/mono';
import { ProblemAlert } from '@/shared/ui/problem-alert';
import { Skeleton } from '@/shared/ui/skeleton';

import { useQueueNav } from './use-queue-nav';

const ROUTE = '/queue/$supplierProductId' as const;

export function ReviewPage() {
  const { supplierProductId } = useParams({ from: ROUTE });
  const search = useSearch({ from: ROUTE });
  const navigate = useNavigate();

  const nav = useQueueNav(supplierProductId);
  // Candidate canonical: from the URL (survives refresh), else the cached queue item.
  const canonicalId = search.candidate ?? nav.current?.canonical_product_id ?? '';

  const product = useSupplierProduct(supplierProductId);
  const canonical = useCanonicalProduct(canonicalId, canonicalId !== '');
  const linked = useSupplierProductsByCanonical(canonicalId, canonicalId !== '');
  const decide = useDecide();
  const [createOpen, setCreateOpen] = useState(false);

  function goToItem(target: CurationItem | undefined): void {
    if (target) {
      void navigate({
        to: ROUTE,
        params: { supplierProductId: target.supplier_product_id },
        search: { candidate: target.canonical_product_id },
      });
    } else {
      void navigate({ to: '/queue' });
    }
  }

  function onDecide(kind: Decision): void {
    const next = nav.next;
    void decide(supplierProductId, kind); // settles in the background
    goToItem(next); // optimistic: move on immediately (curation-ui-plan §3.3)
  }

  useHotkeys({
    c: () => {
      onDecide('confirm');
    },
    r: () => {
      onDecide('reject');
    },
    Escape: () => void navigate({ to: '/queue' }),
    ArrowRight: () => {
      goToItem(nav.next);
    },
    ArrowLeft: () => {
      goToItem(nav.prev);
    },
  });

  return (
    <div className="mx-auto max-w-6xl p-4 pb-24">
      <header className="mb-4 flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => void navigate({ to: '/queue' })}>
          ← {t.review.back}
        </Button>
        {nav.current ? <MethodBadge method={nav.current.method} /> : null}
        {nav.current ? <ConfidenceBadge confidence={nav.current.confidence} /> : null}
        <Mono value={supplierProductId} className="ml-auto" />
      </header>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>{t.review.supplierSide}</CardHeader>
          <CardBody>
            {product.isPending ? (
              <Skeleton className="h-40 w-full" />
            ) : product.isError ? (
              <ProblemAlert error={product.error} onRetry={() => void product.refetch()} />
            ) : (
              <SupplierProductCard product={product.data} />
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader>{t.review.diff}</CardHeader>
          <CardBody>
            {product.isPending ? (
              <Skeleton className="h-40 w-full" />
            ) : product.isError ? (
              <p className="text-sm text-muted">{t.common.none}</p>
            ) : (
              <AttributeDiffTable supplier={product.data} canonical={canonical.data ?? null} />
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader>{t.review.candidateSide}</CardHeader>
          <CardBody className="flex flex-col gap-4">
            {canonicalId === '' ? (
              <p className="text-sm text-muted">{t.common.none}</p>
            ) : canonical.isPending ? (
              <Skeleton className="h-32 w-full" />
            ) : canonical.isError ? (
              <ProblemAlert error={canonical.error} onRetry={() => void canonical.refetch()} />
            ) : (
              <CanonicalProductCard product={canonical.data} />
            )}

            {linked.data && linked.data.items.length > 0 ? (
              <div>
                <p className="mb-1 text-xs font-semibold text-muted uppercase">
                  {t.review.linkedProducts}
                </p>
                <ul className="flex flex-col gap-1">
                  {linked.data.items.map((sp) => (
                    <li key={sp.supplier_product_id} className="text-sm text-text">
                      {sp.name} <span className="text-xs text-muted">({sp.supplier_code})</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </CardBody>
        </Card>
      </div>

      <Card className="mt-4">
        <CardHeader>{t.review.commercial}</CardHeader>
        <CardBody>
          <OffersPanel supplierProductId={supplierProductId} />
        </CardBody>
      </Card>

      {/* Sticky decision bar */}
      <div className="fixed inset-x-0 bottom-0 border-t border-border bg-surface/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-3 p-3">
          <Button
            variant="success"
            onClick={() => {
              onDecide('confirm');
            }}
          >
            {t.review.confirm} <Kbd>c</Kbd>
          </Button>
          <Button
            variant="danger"
            onClick={() => {
              onDecide('reject');
            }}
          >
            {t.review.reject} <Kbd>r</Kbd>
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              setCreateOpen(true);
            }}
          >
            {t.review.createNew}
          </Button>
          <Button
            variant="ghost"
            onClick={() => {
              goToItem(nav.next);
            }}
          >
            {t.review.skip} <Kbd>→</Kbd>
          </Button>
          <span className="ml-auto text-xs text-muted">
            <Kbd>Esc</Kbd> {t.review.back}
          </span>
        </div>
      </div>

      <CreateNewDialog
        open={createOpen}
        supplierProductId={supplierProductId}
        product={product.data}
        onClose={() => {
          setCreateOpen(false);
        }}
        onCreated={() => {
          setCreateOpen(false);
          goToItem(nav.next);
        }}
      />
    </div>
  );
}
