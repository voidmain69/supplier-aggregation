import { describe, expect, it } from 'vitest';

import { buildDiff } from './diff';
import type { CanonicalProduct, SupplierProduct } from '@/shared/api/types';

const supplier: SupplierProduct = {
  supplier_product_id: '01SP',
  supplier_code: 'brain',
  external_id: 'X1',
  external_code: null,
  articul: 'MPN-1',
  gtin: '04006381333931',
  name: 'Widget Pro',
  brand: 'Acme',
  supplier_category_id: null,
  attributes: { color: 'black', weight: '1kg' },
  canonical_product_id: null,
};

describe('buildDiff', () => {
  it('marks a shared GTIN as a match and a differing brand as a mismatch', () => {
    const canonical: CanonicalProduct = {
      canonical_product_id: '01CP',
      gtin: '04006381333931',
      brand: 'Globex',
      title: 'Widget Pro',
    };
    const rows = buildDiff(supplier, canonical);
    const byKey = Object.fromEntries(rows.map((r) => [r.key, r]));

    expect(byKey.GTIN?.status).toBe('match');
    expect(byKey.Бренд?.status).toBe('mismatch');
    expect(byKey.Назва?.status).toBe('match');
  });

  it('lists supplier attributes as supplier-only and pins identity fields first', () => {
    const rows = buildDiff(supplier, null);
    expect(rows.slice(0, 4).every((r) => r.pinned)).toBe(true);
    const color = rows.find((r) => r.key === 'color');
    expect(color?.status).toBe('supplier_only');
    expect(color?.supplier).toBe('black');
  });
});
