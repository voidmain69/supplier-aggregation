import type { CanonicalProduct } from '@/shared/api/types';
import { t } from '@/shared/config/i18n';
import { Field } from '@/shared/ui/field';
import { Mono } from '@/shared/ui/mono';

/** Canonical rendering of a canonical (platform) product — the candidate side of a review. */
export function CanonicalProductCard({ product }: { product: CanonicalProduct }) {
  return (
    <div className="flex flex-col gap-2">
      <div>
        <h3 className="text-base font-semibold text-text">{product.title}</h3>
        <p className="text-sm text-muted">{product.brand ?? t.common.none}</p>
      </div>
      <div className="divide-y divide-border">
        <Field label={t.common.gtin}>
          <Mono value={product.gtin} />
        </Field>
        <Field label="canonical_id">
          <Mono value={product.canonical_product_id} />
        </Field>
      </div>
    </div>
  );
}
