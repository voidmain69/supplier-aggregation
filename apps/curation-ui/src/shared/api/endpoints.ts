/**
 * Typed wrappers over the api-gateway routes. One function per gateway operation; these are the
 * only functions the rest of the app calls to reach the network. Paths and scopes match
 * services/api-gateway/openapi.json.
 */

import { http } from './http';
import type {
  CanonicalProduct,
  CreateCanonicalInput,
  CurationItem,
  CurationStats,
  Decision,
  LinkDecision,
  MergeResult,
  Offer,
  Page,
  PricePoint,
  SupplierProduct,
} from './types';

export interface PageParams {
  cursor?: string | null;
  limit?: number;
}

// -------------------------------------------------------------------------- curation
export function getCurationStats(): Promise<CurationStats> {
  return http.get('/v1/curation/stats');
}

export function getCurationQueue(params: PageParams = {}): Promise<Page<CurationItem>> {
  return http.get('/v1/curation/queue', { params: { cursor: params.cursor, limit: params.limit } });
}

export function getDecisions(
  params: { supplierProductId?: string } & PageParams = {},
): Promise<Page<Decision>> {
  return http.get('/v1/curation/decisions', {
    params: {
      supplier_product_id: params.supplierProductId,
      cursor: params.cursor,
      limit: params.limit,
    },
  });
}

export function confirmLink(supplierProductId: string): Promise<LinkDecision> {
  return http.post(`/v1/curation/links/${encodeURIComponent(supplierProductId)}/confirm`);
}

export function rejectLink(supplierProductId: string): Promise<LinkDecision> {
  return http.post(`/v1/curation/links/${encodeURIComponent(supplierProductId)}/reject`);
}

export function createNewCanonical(
  supplierProductId: string,
  body: CreateCanonicalInput,
): Promise<LinkDecision> {
  return http.post(`/v1/curation/links/${encodeURIComponent(supplierProductId)}/create-new`, {
    body,
  });
}

export function mergeCanonical(
  targetCanonicalId: string,
  sourceCanonicalId: string,
): Promise<MergeResult> {
  return http.post(`/v1/canonical-products/${encodeURIComponent(targetCanonicalId)}/merge`, {
    body: { source_canonical_product_id: sourceCanonicalId },
  });
}

// --------------------------------------------------------------------------- catalog
export function getSupplierProduct(id: string): Promise<SupplierProduct> {
  return http.get(`/v1/products/${encodeURIComponent(id)}`);
}

export function listSupplierProducts(
  params: { canonicalProductId?: string; supplier?: string } & PageParams,
): Promise<Page<SupplierProduct>> {
  return http.get('/v1/products', {
    params: {
      canonical_product_id: params.canonicalProductId,
      supplier: params.supplier,
      cursor: params.cursor,
      limit: params.limit,
    },
  });
}

// ------------------------------------------------------------------ canonical products
export function getCanonicalProduct(id: string): Promise<CanonicalProduct> {
  return http.get(`/v1/canonical-products/${encodeURIComponent(id)}`);
}

export function listCanonicalProducts(
  params: { gtin?: string } & PageParams = {},
): Promise<Page<CanonicalProduct>> {
  return http.get('/v1/canonical-products', {
    params: { gtin: params.gtin, cursor: params.cursor, limit: params.limit },
  });
}

// ---------------------------------------------------------------------------- offers
export function listProductOffers(
  supplierProductId: string,
  params: PageParams = {},
): Promise<Page<Offer>> {
  return http.get(`/v1/products/${encodeURIComponent(supplierProductId)}/offers`, {
    params: { cursor: params.cursor, limit: params.limit },
  });
}

// ----------------------------------------------------------------------- price history
export function getOfferPriceHistory(
  offerId: string,
  params: { from?: string; to?: string } & PageParams = {},
): Promise<Page<PricePoint>> {
  return http.get(`/v1/offers/${encodeURIComponent(offerId)}/price-history`, {
    params: { from: params.from, to: params.to, cursor: params.cursor, limit: params.limit },
  });
}
