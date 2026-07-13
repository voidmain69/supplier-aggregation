import { Link } from '@tanstack/react-router';
import { useState } from 'react';

import { useCanonicalList } from '@/entities/canonical-product/use-canonical-product';
import { t } from '@/shared/config/i18n';
import { Button } from '@/shared/ui/button';
import { Card } from '@/shared/ui/card';
import { EmptyState } from '@/shared/ui/empty-state';
import { Mono } from '@/shared/ui/mono';
import { ProblemAlert } from '@/shared/ui/problem-alert';
import { Skeleton } from '@/shared/ui/skeleton';

export function CanonicalListPage() {
  const [gtin, setGtin] = useState('');
  const list = useCanonicalList(gtin);

  return (
    <div className="mx-auto max-w-4xl p-4">
      <h1 className="mb-4 text-xl font-semibold text-text">{t.canonical.title}</h1>
      <input
        value={gtin}
        onChange={(e) => {
          setGtin(e.target.value.replace(/\D/g, ''));
        }}
        placeholder={t.canonical.searchGtin}
        inputMode="numeric"
        className="mb-4 h-10 w-full rounded-md border border-border bg-surface px-3 font-mono text-sm text-text outline-none focus:border-accent"
      />

      {list.isPending ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : list.isError ? (
        <ProblemAlert error={list.error} onRetry={() => void list.refetch()} />
      ) : list.items.length === 0 ? (
        <EmptyState title={t.canonical.empty} />
      ) : (
        <Card>
          <ul className="divide-y divide-border">
            {list.items.map((cp) => (
              <li key={cp.canonical_product_id}>
                <Link
                  to="/canonical/$canonicalId"
                  params={{ canonicalId: cp.canonical_product_id }}
                  className="flex items-center justify-between gap-4 px-4 py-3 hover:bg-surface-2"
                >
                  <div>
                    <div className="text-sm font-medium text-text">{cp.title}</div>
                    <div className="text-xs text-muted">{cp.brand ?? ''}</div>
                  </div>
                  <Mono value={cp.gtin} />
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {list.hasNextPage ? (
        <div className="mt-4 flex justify-center">
          <Button
            variant="outline"
            onClick={() => void list.fetchNextPage()}
            disabled={list.isFetchingNextPage}
          >
            {list.isFetchingNextPage ? t.common.loading : t.queue.loadMore}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
