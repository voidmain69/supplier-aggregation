import type { ReactNode } from 'react';

/** A compact label/value row for the dense product cards. */
export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1">
      <span className="shrink-0 text-xs text-muted">{label}</span>
      <span className="text-right text-sm text-text">{children}</span>
    </div>
  );
}
