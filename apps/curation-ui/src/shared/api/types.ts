/**
 * Response DTOs for the api-gateway surface.
 *
 * The gateway relays downstream responses verbatim (it owns no data), so its OpenAPI types the
 * request params and the `Problem` error body but NOT the response payloads. These interfaces
 * therefore mirror the downstream service contracts (matching / catalog / offer / price-history)
 * that the gateway proxies. Keep them in sync when a downstream response schema changes.
 *
 * The one type we pull straight from the generated contract is `ApiProblem`, so the error shape
 * can never silently drift from the gateway's OpenAPI.
 */

import type { components } from './schema.gen';

/** RFC 9457 problem+json body — sourced from the generated gateway contract. */
export type ApiProblem = components['schemas']['Problem'];

/** Cursor-paginated envelope (libs/core Page[T]). `next_cursor` is null on the last page. */
export interface Page<T> {
  items: T[];
  next_cursor: string | null;
  total_estimate: number | null;
}

/** A supplier product as the catalog service exposes it (mirrors SupplierProductOut). */
export interface SupplierProduct {
  supplier_product_id: string;
  supplier_code: string;
  external_id: string;
  external_code: string | null;
  articul: string | null;
  gtin: string | null;
  name: string;
  brand: string | null;
  supplier_category_id: string | null;
  attributes: Record<string, unknown>;
  canonical_product_id: string | null;
}

/** A canonical product (mirrors CanonicalProductOut from the matching service). */
export interface CanonicalProduct {
  canonical_product_id: string;
  gtin: string | null;
  brand: string | null;
  title: string;
}

/** A supplier→canonical link awaiting a decision (mirrors CurationItemOut). */
export interface CurationItem {
  supplier_product_id: string;
  canonical_product_id: string;
  method: string;
  confidence: number;
  status: string;
}

/** The outcome of a confirm/reject decision (mirrors LinkDecisionOut). */
export interface LinkDecision {
  supplier_product_id: string;
  canonical_product_id: string;
  status: string;
}

/** One entry in the curation decision journal (mirrors DecisionOut from the matching service). */
export interface Decision {
  decision_id: string;
  action: string;
  supplier_product_id: string | null;
  canonical_product_id: string;
  method: string | null;
  confidence: number | null;
  operator: string;
  note: string | null;
  decided_at: string;
}

/** Body for creating a brand-new canonical from a curation item (mirrors CreateCanonicalIn). */
export interface CreateCanonicalInput {
  title: string;
  brand: string | null;
  gtin: string | null;
}

/** Outcome of merging one canonical into another (mirrors MergeResultOut). */
export interface MergeResult {
  target_canonical_product_id: string;
  source_canonical_product_id: string;
  moved_links: number;
}

/** A supplier-account offer (mirrors OfferOut). Money fields are decimal strings. */
export interface Offer {
  offer_id: string;
  supplier_account_id: string;
  supplier_product_id: string;
  price: string;
  currency: string;
  price_uah: string | null;
  rrp_uah: string | null;
  observed_at: string;
}

/** One observed price point (mirrors PricePointOut). */
export interface PricePoint {
  offer_id: string;
  ts: string;
  price: string;
  currency: string;
  price_uah: string | null;
}
