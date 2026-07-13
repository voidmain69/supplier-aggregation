import { t } from '@/shared/config/i18n';
import { cn } from '@/shared/ui/cn';

import { buildDiff, type DiffRow, type DiffStatus } from './diff';
import type { CanonicalProduct, SupplierProduct } from '@/shared/api/types';

const STATUS_STYLE: Record<DiffStatus, string> = {
  match: 'text-success',
  mismatch: 'text-danger font-medium',
  supplier_only: 'text-muted',
  canonical_only: 'text-muted',
};

const STATUS_MARK: Record<DiffStatus, string> = {
  match: '=',
  mismatch: '≠',
  supplier_only: '‹',
  canonical_only: '›',
};

function Cell({ value }: { value: string | null }) {
  return <span className={value ? '' : 'text-muted'}>{value ?? t.common.none}</span>;
}

function DiffRowView({ row }: { row: DiffRow }) {
  return (
    <tr className="border-b border-border last:border-0">
      <td className="py-1 pr-2 align-top text-xs text-muted">{row.key}</td>
      <td className={cn('py-1 px-2 align-top text-sm', STATUS_STYLE[row.status])}>
        <Cell value={row.supplier} />
      </td>
      <td className="py-1 px-1 text-center align-top" aria-label={row.status}>
        <span className={STATUS_STYLE[row.status]}>{STATUS_MARK[row.status]}</span>
      </td>
      <td className={cn('py-1 pl-2 align-top text-sm', STATUS_STYLE[row.status])}>
        <Cell value={row.canonical} />
      </td>
    </tr>
  );
}

/** Row-per-attribute comparison; identity fields pinned on top, mismatches flagged in red. */
export function AttributeDiffTable({
  supplier,
  canonical,
}: {
  supplier: SupplierProduct;
  canonical: CanonicalProduct | null;
}) {
  const rows = buildDiff(supplier, canonical);
  const pinned = rows.filter((r) => r.pinned);
  const rest = rows.filter((r) => !r.pinned);
  return (
    <table className="w-full border-collapse text-left">
      <thead>
        <tr className="text-xs text-muted">
          <th className="pb-1 font-normal">{t.common.attributes}</th>
          <th className="px-2 pb-1 font-normal">{t.review.supplierSide}</th>
          <th aria-hidden="true"></th>
          <th className="pl-2 pb-1 font-normal">{t.review.candidateSide}</th>
        </tr>
      </thead>
      <tbody>
        {[...pinned, ...rest].map((r) => (
          <DiffRowView key={r.key} row={r} />
        ))}
      </tbody>
    </table>
  );
}
