import { useMemo, useState } from 'react';

import { ActionBadge } from '@/entities/decision/action-badge';
import { useDecisions } from '@/entities/decision/use-decisions';
import type { Decision } from '@/shared/api/types';
import { t } from '@/shared/config/i18n';
import { timeAgo } from '@/shared/lib/format';
import { Button } from '@/shared/ui/button';
import { Card } from '@/shared/ui/card';
import { cn } from '@/shared/ui/cn';
import { EmptyState } from '@/shared/ui/empty-state';
import { Mono } from '@/shared/ui/mono';
import { ProblemAlert } from '@/shared/ui/problem-alert';
import { Skeleton } from '@/shared/ui/skeleton';

type Filter = 'all' | 'confirm' | 'reject' | 'create_new' | 'merge';
const FILTERS: readonly Filter[] = ['all', 'confirm', 'reject', 'create_new', 'merge'];

/** The curation decision journal: an append-only audit of confirm/reject/create-new/merge. */
export function DecisionsPage() {
  const decisions = useDecisions();
  const [filter, setFilter] = useState<Filter>('all');

  const visible = useMemo(
    () => (filter === 'all' ? decisions.items : decisions.items.filter((d) => d.action === filter)),
    [decisions.items, filter],
  );

  return (
    <div className="mx-auto max-w-5xl p-4">
      <header className="mb-4 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-text">{t.decisions.title}</h1>
          <p className="text-sm text-muted">{t.decisions.subtitle}</p>
        </div>
        <div className="flex flex-wrap gap-1" role="tablist" aria-label={t.decisions.title}>
          {FILTERS.map((f) => (
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
              {t.decisions.filters[f]}
            </button>
          ))}
        </div>
      </header>

      {decisions.isPending ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 8 }, (_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : decisions.isError ? (
        <ProblemAlert error={decisions.error} onRetry={() => void decisions.refetch()} />
      ) : visible.length === 0 ? (
        <EmptyState title={t.decisions.empty} hint={t.decisions.emptyHint} />
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="text-left text-xs text-muted">
                  <th className="px-3 py-2 font-normal">{t.decisions.columns.when}</th>
                  <th className="px-3 py-2 font-normal">{t.decisions.columns.action}</th>
                  <th className="px-3 py-2 font-normal">{t.decisions.columns.product}</th>
                  <th className="px-3 py-2 font-normal">{t.decisions.columns.canonical}</th>
                  <th className="px-3 py-2 font-normal">{t.decisions.columns.operator}</th>
                  <th className="px-3 py-2 font-normal">{t.decisions.columns.note}</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((d: Decision) => (
                  <tr key={d.decision_id} className="border-t border-border align-top">
                    <td
                      className="px-3 py-2 text-xs whitespace-nowrap text-muted"
                      title={d.decided_at}
                    >
                      {timeAgo(d.decided_at)}
                    </td>
                    <td className="px-3 py-2">
                      <ActionBadge action={d.action} />
                    </td>
                    <td className="px-3 py-2">
                      <Mono value={d.supplier_product_id} />
                    </td>
                    <td className="px-3 py-2">
                      <Mono value={d.canonical_product_id} />
                    </td>
                    <td className="px-3 py-2 text-sm whitespace-nowrap text-text">{d.operator}</td>
                    <td className="px-3 py-2 text-sm text-muted">{d.note ?? t.common.none}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {decisions.hasNextPage ? (
        <div className="mt-4 flex justify-center">
          <Button
            variant="outline"
            onClick={() => void decisions.fetchNextPage()}
            disabled={decisions.isFetchingNextPage}
          >
            {decisions.isFetchingNextPage ? t.common.loading : t.decisions.loadMore}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
