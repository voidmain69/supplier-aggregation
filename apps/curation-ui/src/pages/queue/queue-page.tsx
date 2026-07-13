import { useNavigate } from '@tanstack/react-router';
import { useMemo, useState } from 'react';

import { useQueue } from '@/entities/curation/use-queue';
import type { CurationItem } from '@/shared/api/types';
import { t } from '@/shared/config/i18n';
import { useHotkeys } from '@/shared/lib/use-hotkeys';
import { Button } from '@/shared/ui/button';
import { Card } from '@/shared/ui/card';
import { cn } from '@/shared/ui/cn';
import { EmptyState } from '@/shared/ui/empty-state';
import { Kbd } from '@/shared/ui/kbd';
import { ProblemAlert } from '@/shared/ui/problem-alert';
import { Skeleton } from '@/shared/ui/skeleton';

import { QueueRow } from './queue-row';

type Filter = 'all' | 'rag' | 'collision';

function matchesFilter(item: CurationItem, filter: Filter): boolean {
  if (filter === 'rag') return item.method === 'rag_suggested';
  if (filter === 'collision') return item.method === 'gtin_auto';
  return true;
}

export function QueuePage() {
  const navigate = useNavigate();
  const queue = useQueue();
  const [filter, setFilter] = useState<Filter>('all');
  const [selected, setSelected] = useState(0);

  const visible = useMemo(
    () => queue.items.filter((item) => matchesFilter(item, filter)),
    [queue.items, filter],
  );

  const clamped = Math.min(selected, Math.max(0, visible.length - 1));

  useHotkeys(
    {
      j: () => {
        setSelected((s) => Math.min(s + 1, visible.length - 1));
      },
      k: () => {
        setSelected((s) => Math.max(s - 1, 0));
      },
      Enter: () => {
        const item = visible[clamped];
        if (item) {
          void navigate({
            to: '/queue/$supplierProductId',
            params: { supplierProductId: item.supplier_product_id },
          });
        }
      },
    },
    visible.length > 0,
  );

  const depth =
    queue.totalEstimate ?? (queue.hasNextPage ? `${String(visible.length)}+` : visible.length);

  return (
    <div className="mx-auto max-w-5xl p-4">
      <header className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text">{t.queue.title}</h1>
          <p className="text-sm text-muted">{t.queue.depth(depth)}</p>
        </div>
        <div className="flex gap-1" role="tablist" aria-label={t.queue.title}>
          {(['all', 'rag', 'collision'] as const).map((f) => (
            <button
              key={f}
              role="tab"
              aria-selected={filter === f}
              onClick={() => {
                setFilter(f);
              }}
              className={cn(
                'rounded-md px-3 py-1 text-sm',
                filter === f ? 'bg-accent text-accent-fg' : 'text-muted hover:bg-surface-2',
              )}
            >
              {t.queue.filters[f]}
            </button>
          ))}
        </div>
      </header>

      <p className="mb-2 text-xs text-muted">
        <Kbd>j</Kbd> <Kbd>k</Kbd> навігація · <Kbd>Enter</Kbd> {t.queue.open}
      </p>

      {queue.isPending ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 8 }, (_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : queue.isError ? (
        <ProblemAlert error={queue.error} onRetry={() => void queue.refetch()} />
      ) : visible.length === 0 ? (
        <EmptyState title={t.queue.empty} hint={t.queue.emptyHint} />
      ) : (
        <Card>
          <table className="w-full border-collapse">
            <thead>
              <tr className="text-left text-xs text-muted">
                <th className="px-3 py-2 font-normal">{t.queue.columns.product}</th>
                <th className="px-3 py-2 font-normal">{t.queue.columns.candidate}</th>
                <th className="px-3 py-2 font-normal">{t.queue.columns.method}</th>
                <th className="px-3 py-2 font-normal">{t.queue.columns.confidence}</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((item, i) => (
                <QueueRow key={item.supplier_product_id} item={item} selected={i === clamped} />
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {queue.hasNextPage ? (
        <div className="mt-4 flex justify-center">
          <Button
            variant="outline"
            onClick={() => void queue.fetchNextPage()}
            disabled={queue.isFetchingNextPage}
          >
            {queue.isFetchingNextPage ? t.common.loading : t.queue.loadMore}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
