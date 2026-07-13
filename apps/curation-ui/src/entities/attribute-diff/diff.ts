/**
 * Build the supplier↔candidate comparison shown in the review workspace.
 *
 * The canonical DTO exposes only gtin/brand/title, so those shared fields are compared directly
 * (a strong confirm/reject signal), and the supplier's own attributes are listed as
 * supplier-only context. When the canonical contract grows attribute-level fields, extend the
 * `canonical` side here — the table renders whatever rows this returns.
 */

import type { CanonicalProduct, SupplierProduct } from '@/shared/api/types';

export type DiffStatus = 'match' | 'mismatch' | 'supplier_only' | 'canonical_only';

export interface DiffRow {
  key: string;
  supplier: string | null;
  canonical: string | null;
  status: DiffStatus;
  /** Pinned rows (GTIN/brand/MPN) sort to the top — the identity signals. */
  pinned: boolean;
}

function toText(value: unknown): string | null {
  if (value === null || value === undefined || value === '') return null;
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') {
    return String(value);
  }
  return JSON.stringify(value);
}

function statusOf(supplier: string | null, canonical: string | null): DiffStatus {
  if (supplier !== null && canonical !== null) {
    return supplier.trim().toLowerCase() === canonical.trim().toLowerCase() ? 'match' : 'mismatch';
  }
  if (supplier !== null) return 'supplier_only';
  return 'canonical_only';
}

function row(
  key: string,
  supplier: string | null,
  canonical: string | null,
  pinned = false,
): DiffRow {
  return { key, supplier, canonical, status: statusOf(supplier, canonical), pinned };
}

export function buildDiff(
  supplier: SupplierProduct,
  canonical: CanonicalProduct | null,
): DiffRow[] {
  const rows: DiffRow[] = [
    row('GTIN', toText(supplier.gtin), toText(canonical?.gtin ?? null), true),
    row('Бренд', toText(supplier.brand), toText(canonical?.brand ?? null), true),
    row('Артикул (MPN)', toText(supplier.articul), null, true),
    row('Назва', toText(supplier.name), toText(canonical?.title ?? null), true),
  ];
  for (const [key, value] of Object.entries(supplier.attributes)) {
    rows.push(row(key, toText(value), null));
  }
  return rows;
}
