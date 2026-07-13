import { useSyncAccounts } from '@/entities/sync/use-sync-accounts';
import { useTriggerSync } from '@/features/sync-trigger/use-trigger';
import { t } from '@/shared/config/i18n';
import { timeAgo } from '@/shared/lib/format';
import { Badge, type BadgeTone } from '@/shared/ui/badge';
import { Button } from '@/shared/ui/button';
import { Card } from '@/shared/ui/card';
import { EmptyState } from '@/shared/ui/empty-state';
import { Mono } from '@/shared/ui/mono';
import { ProblemAlert } from '@/shared/ui/problem-alert';
import { Skeleton } from '@/shared/ui/skeleton';

const STATUS_TONE: Record<string, BadgeTone> = {
  never: 'neutral',
  ok: 'success',
  overdue: 'danger',
};

function TriggerButton({ accountId }: { accountId: string }) {
  const trigger = useTriggerSync();
  return (
    <Button
      variant="outline"
      onClick={() => {
        trigger.mutate(accountId);
      }}
      disabled={trigger.isPending}
    >
      {trigger.isPending ? t.sync.triggering : t.sync.trigger}
    </Button>
  );
}

/** Sync monitoring: per-account status with a manual "sync now" trigger. */
export function SyncPage() {
  const accounts = useSyncAccounts();

  return (
    <div className="mx-auto max-w-5xl p-4">
      <header className="mb-4">
        <h1 className="text-xl font-semibold text-text">{t.sync.title}</h1>
        <p className="text-sm text-muted">{t.sync.subtitle}</p>
      </header>

      {accounts.isPending ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 5 }, (_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : accounts.isError ? (
        <ProblemAlert error={accounts.error} onRetry={() => void accounts.refetch()} />
      ) : accounts.data.length === 0 ? (
        <EmptyState title={t.sync.empty} hint={t.sync.emptyHint} />
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="text-left text-xs text-muted">
                  <th className="px-3 py-2 font-normal">{t.sync.columns.account}</th>
                  <th className="px-3 py-2 font-normal">{t.sync.columns.supplier}</th>
                  <th className="px-3 py-2 font-normal">{t.sync.columns.mode}</th>
                  <th className="px-3 py-2 font-normal">{t.sync.columns.lastSync}</th>
                  <th className="px-3 py-2 font-normal">{t.sync.columns.status}</th>
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody>
                {accounts.data.map((account) => (
                  <tr key={account.account_id} className="border-t border-border">
                    <td className="px-3 py-2">
                      <Mono value={account.account_id} />
                    </td>
                    <td className="px-3 py-2 text-sm text-text">{account.supplier_code}</td>
                    <td className="px-3 py-2 text-sm text-muted">{account.mode}</td>
                    <td className="px-3 py-2 text-xs whitespace-nowrap text-muted">
                      {account.last_requested_at
                        ? timeAgo(account.last_requested_at)
                        : t.sync.never}
                    </td>
                    <td className="px-3 py-2">
                      <Badge tone={STATUS_TONE[account.status] ?? 'neutral'}>
                        {t.sync.status[account.status] ?? account.status}
                      </Badge>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <TriggerButton accountId={account.account_id} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
