import type { SupplierProduct } from '@/shared/api/types';
import { t } from '@/shared/config/i18n';
import { Badge } from '@/shared/ui/badge';
import { Field } from '@/shared/ui/field';
import { Mono } from '@/shared/ui/mono';

/** Canonical rendering of a supplier product. Reused wherever a supplier product appears. */
export function SupplierProductCard({ product }: { product: SupplierProduct }) {
  return (
    <div className="flex flex-col gap-2">
      <div>
        <h3 className="text-base font-semibold text-text">{product.name}</h3>
        <p className="text-sm text-muted">{product.brand ?? t.common.none}</p>
      </div>
      <div className="divide-y divide-border">
        <Field label={t.common.gtin}>
          <Mono value={product.gtin} />
        </Field>
        <Field label={t.common.mpn}>
          <Mono value={product.articul} />
        </Field>
        <Field label={t.common.supplier}>
          <Badge tone="neutral">{product.supplier_code}</Badge>
        </Field>
        <Field label="external_id">
          <Mono value={product.external_id} />
        </Field>
        <Field label={t.common.category}>
          <Mono value={product.supplier_category_id} />
        </Field>
      </div>
    </div>
  );
}
