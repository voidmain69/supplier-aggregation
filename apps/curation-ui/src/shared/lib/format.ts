/** Presentation helpers: money, relative time, confidence banding. Pure, no I/O. */

import { t } from '@/shared/config/i18n';

export type ConfidenceBand = 'high' | 'medium' | 'low';

/** Confidence → band, using the ADR-0004 thresholds (>=0.85 strong, >=0.65 candidate). */
export function confidenceBand(confidence: number): ConfidenceBand {
  if (confidence >= 0.85) return 'high';
  if (confidence >= 0.65) return 'medium';
  return 'low';
}

/** Format a decimal-string amount (server sends money as strings) with an ISO-4217 code. */
export function formatMoney(amount: string | null, currency: string): string {
  if (amount === null) return t.common.none;
  const n = Number(amount);
  if (Number.isNaN(n)) return `${amount} ${currency}`;
  return `${n.toLocaleString('uk-UA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`;
}

/** Human-readable "time ago" in Ukrainian from an ISO 8601 UTC timestamp. */
export function timeAgo(iso: string, now: number = Date.now()): string {
  const diffMs = now - new Date(iso).getTime();
  const sec = Math.max(0, Math.round(diffMs / 1000));
  if (sec < 60) return 'щойно';
  const min = Math.round(sec / 60);
  if (min < 60) return `${String(min)} хв тому`;
  const hrs = Math.round(min / 60);
  if (hrs < 24) return `${String(hrs)} год тому`;
  const days = Math.round(hrs / 24);
  return `${String(days)} дн тому`;
}
