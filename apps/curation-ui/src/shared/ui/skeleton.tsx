import { cn } from './cn';

/** Loading placeholder — a calm skeleton, not a spinner (curation-ui-plan §9.2). */
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded bg-surface-2', className)} />;
}
