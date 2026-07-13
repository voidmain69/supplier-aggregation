/**
 * Central query-key factory (curation-ui-plan §4.3): one place to derive keys so cache
 * invalidation after a decision touches exactly the right entries and nothing over-refetches.
 */

export const queryKeys = {
  curationQueue: () => ['curation', 'queue'] as const,
  curationStats: () => ['curation', 'stats'] as const,
  decisions: () => ['curation', 'decisions'] as const,
  supplierProduct: (id: string) => ['supplier-product', id] as const,
  supplierProductsByCanonical: (canonicalId: string) =>
    ['supplier-products', 'by-canonical', canonicalId] as const,
  canonicalProduct: (id: string) => ['canonical-product', id] as const,
  canonicalList: (gtin: string) => ['canonical-products', 'list', gtin] as const,
  productOffers: (supplierProductId: string) => ['offers', supplierProductId] as const,
  priceHistory: (offerId: string) => ['price-history', offerId] as const,
  syncAccounts: () => ['sync', 'accounts'] as const,
};
