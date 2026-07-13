import { ApiError } from '@/shared/api/http';
import { t } from '@/shared/config/i18n';

import { Button } from './button';

/**
 * Standard error surface. Renders the problem+json `detail` and the `trace_id` so an operator
 * can quote it to support — the UI-side end of the traceparent link (curation-ui-plan §7).
 */
export function ProblemAlert({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const detail =
    error instanceof ApiError ? (error.problem?.detail ?? error.message) : t.common.errorTitle;
  const traceId = error instanceof ApiError ? error.traceId : null;

  return (
    <div className="rounded-md border border-danger bg-danger-bg p-4" role="alert">
      <p className="font-medium text-danger">{t.common.errorTitle}</p>
      <p className="mt-1 text-sm text-text">{detail}</p>
      {traceId ? (
        <p className="mt-2 text-xs text-muted">
          {t.common.traceHint} <span className="font-mono">{traceId}</span>
        </p>
      ) : null}
      {onRetry ? (
        <Button size="sm" variant="outline" className="mt-3" onClick={onRetry}>
          {t.common.retry}
        </Button>
      ) : null}
    </div>
  );
}
