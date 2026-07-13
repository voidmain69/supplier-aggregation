import type { Offer } from '@/shared/api/types';
import { usePriceHistory } from '@/entities/price-history/use-price-history';
import { PriceSparkline } from '@/entities/price-history/price-sparkline';
import { useProductOffers } from '@/entities/offer/use-offers';
import { t } from '@/shared/config/i18n';
import { formatMoney, timeAgo } from '@/shared/lib/format';
import { Mono } from '@/shared/ui/mono';
import { ProblemAlert } from '@/shared/ui/problem-alert';
import { Skeleton } from '@/shared/ui/skeleton';

function OfferRow({ offer }: { offer: Offer }) {
  const history = usePriceHistory(offer.offer_id);
  return (
    <div className="flex items-center justify-between gap-4 border-b border-border py-2 last:border-0">
      <div className="min-w-0">
        <div className="text-sm font-medium text-text">{formatMoney(offer.price_uah, 'UAH')}</div>
        <div className="truncate text-xs text-muted">
          <Mono value={offer.supplier_account_id} /> · {timeAgo(offer.observed_at)}
        </div>
      </div>
      <div className="shrink-0">
        {history.isPending ? (
          <Skeleton className="h-8 w-40" />
        ) : history.isError ? (
          <span className="text-xs text-muted">—</span>
        ) : (
          <PriceSparkline points={history.data.items} />
        )}
      </div>
    </div>
  );
}

/**
 * Commercial context for a review: offers for the supplier product plus a per-offer price
 * sparkline. A price wildly different from a "similar" candidate is a strong not-a-match signal
 * (curation-ui-plan §3.3).
 */
export function OffersPanel({ supplierProductId }: { supplierProductId: string }) {
  const offers = useProductOffers(supplierProductId);

  if (offers.isPending) return <Skeleton className="h-24 w-full" />;
  if (offers.isError)
    return <ProblemAlert error={offers.error} onRetry={() => void offers.refetch()} />;
  if (offers.data.items.length === 0) {
    return <p className="py-4 text-sm text-muted">{t.review.noOffers}</p>;
  }

  return (
    <div>
      {offers.data.items.map((offer) => (
        <OfferRow key={offer.offer_id} offer={offer} />
      ))}
    </div>
  );
}
