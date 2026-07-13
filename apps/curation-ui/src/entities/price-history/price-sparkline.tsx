import type { PricePoint } from '@/shared/api/types';

/**
 * Inline-SVG sparkline of an offer's UAH price over time. No chart library — a handful of points
 * rendered as a polyline keeps this in the lazy charts chunk small (curation-ui-plan §8).
 */
export function PriceSparkline({
  points,
  width = 160,
  height = 32,
}: {
  points: PricePoint[];
  width?: number;
  height?: number;
}) {
  const values = points
    .map((p) => (p.price_uah !== null ? Number(p.price_uah) : NaN))
    .filter((n) => !Number.isNaN(n));

  if (values.length < 2) return <span className="text-xs text-muted">—</span>;

  const first = values[0];
  const last = values[values.length - 1];
  if (first === undefined || last === undefined)
    return <span className="text-xs text-muted">—</span>;

  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const stepX = width / (values.length - 1);

  const path = values
    .map((v, i) => {
      const x = i * stepX;
      const y = height - ((v - min) / span) * height;
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  const trendingUp = last > first;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${String(width)} ${String(height)}`}
      role="img"
      aria-label={`price trend, ${String(values.length)} points`}
      className={trendingUp ? 'text-danger' : 'text-success'}
    >
      <path d={path} fill="none" stroke="currentColor" strokeWidth={1.5} />
    </svg>
  );
}
