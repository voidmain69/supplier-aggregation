import { Link } from '@tanstack/react-router';

import { ActionBadge } from '@/entities/decision/action-badge';
import { useDecisions } from '@/entities/decision/use-decisions';
import { useStats } from '@/entities/stats/use-stats';
import { useSyncAccounts } from '@/entities/sync/use-sync-accounts';
import { t } from '@/shared/config/i18n';
import { timeAgo } from '@/shared/lib/format';
import { Card } from '@/shared/ui/card';
import { Mono } from '@/shared/ui/mono';
import { ProblemAlert } from '@/shared/ui/problem-alert';
import { Skeleton } from '@/shared/ui/skeleton';

const ACTIONS = ['confirm', 'reject', 'create_new', 'merge'] as const;

function StatCard({
  to,
  value,
  label,
  hint,
}: {
  to: '/queue' | '/canonical' | '/decisions' | '/sync';
  value: number | string;
  label: string;
  hint: string;
}) {
  return (
    <Link to={to} className="block">
      <Card className="p-4 transition-colors hover:bg-surface-2">
        <div className="text-2xl font-semibold text-text">{value}</div>
        <div className="text-sm font-medium text-text">{label}</div>
        <div className="text-xs text-muted">{hint}</div>
      </Card>
    </Link>
  );
}

/** Operator dashboard: queue depth, canonical total, decision activity and recent decisions. */
export function DashboardPage() {
  const stats = useStats();
  const recent = useDecisions();
  const sync = useSyncAccounts();
  const recentItems = recent.items.slice(0, 5);
  const overdue = sync.data?.filter((a) => a.status === 'overdue').length ?? 0;

  return (
    <div className="mx-auto max-w-5xl p-4">
      <header className="mb-4">
        <h1 className="text-xl font-semibold text-text">{t.dashboard.title}</h1>
        <p className="text-sm text-muted">{t.dashboard.subtitle}</p>
      </header>

      {stats.isPending ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {Array.from({ length: 3 }, (_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : stats.isError ? (
        <ProblemAlert error={stats.error} onRetry={() => void stats.refetch()} />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              to="/queue"
              value={stats.data.pending_reviews}
              label={t.dashboard.pending}
              hint={t.dashboard.pendingHint}
            />
            <StatCard
              to="/canonical"
              value={stats.data.canonical_products}
              label={t.dashboard.canonical}
              hint={t.dashboard.canonicalHint}
            />
            <StatCard
              to="/decisions"
              value={stats.data.decisions_total}
              label={t.dashboard.decisions}
              hint={t.dashboard.decisionsHint}
            />
            <StatCard
              to="/sync"
              value={sync.isPending ? '…' : overdue}
              label={t.dashboard.sync}
              hint={overdue > 0 ? t.dashboard.syncHint : t.dashboard.syncAllOk}
            />
          </div>

          <Card className="mt-4 p-4">
            <h2 className="mb-2 text-sm font-medium text-text">{t.dashboard.activity}</h2>
            <div className="flex flex-wrap gap-4">
              {ACTIONS.map((a) => (
                <div key={a} className="flex items-center gap-2">
                  <ActionBadge action={a} />
                  <span className="text-sm text-muted">
                    {stats.data.decisions_by_action[a] ?? 0}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}

      <Card className="mt-4 p-4">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-medium text-text">{t.dashboard.recent}</h2>
          <Link to="/decisions" className="text-xs text-accent hover:underline">
            {t.dashboard.seeAll}
          </Link>
        </div>
        {recent.isPending ? (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 5 }, (_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        ) : recentItems.length === 0 ? (
          <p className="text-sm text-muted">{t.dashboard.recentEmpty}</p>
        ) : (
          <ul className="flex flex-col divide-y divide-border">
            {recentItems.map((d) => (
              <li key={d.decision_id} className="flex items-center gap-3 py-2 text-sm">
                <ActionBadge action={d.action} />
                <Mono value={d.supplier_product_id} />
                <span className="ml-auto text-xs text-muted">{timeAgo(d.decided_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
