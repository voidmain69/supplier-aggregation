import type { ReactNode } from 'react';

/** A keyboard-shortcut hint chip. Making shortcuts visible is a core plan requirement (§9.2). */
export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="inline-flex min-w-5 items-center justify-center rounded border border-border bg-surface-2 px-1 font-mono text-xs text-muted">
      {children}
    </kbd>
  );
}
